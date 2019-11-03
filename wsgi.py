from flask import Flask, request, Response
from youtube_transcript_api import YouTubeTranscriptApi as yttapi

import json

from gensim import models, corpora,similarities
from gensim.parsing.preprocessing import STOPWORDS
from bs4 import BeautifulSoup
import requests
from ai.train import AsyncTrainer

app = Flask(__name__)

RL_WEIGHT_FACTOR = 0.01

last_search = ''
rl_network = AsyncTrainer()
rl_network.start_ai()

@app.route('/watch-data',methods=['POST'])
def watch_data():
    global last_search
    req_data = request.get_json()

    video_id = req_data['video_id']
    timescore = req_data['timescore']
    search = req_data['query']

    transcript = yttapi.get_transcript(video_id)
    
    if(isinstance(search,str) == False):
        search = ''

    scored_transcript = process_transcript(transcript,timescore)
       
    return Response(json.dumps(suggest_next_video(video_id,scored_transcript,search),ensure_ascii=False).encode('utf-8'),mimetype='application/json')
    #Some YouTube titles will have emojis etc in it -- safest bet is just to encode to unicode.

@app.route('/searched',methods=['POST'])
def searched():
    global last_search
    req_data = request.get_json()
    last_search = req_data['query']
    
@app.route('/clicked',methods=['POST'])
# Takes a JSON dict of the form {"sel": I, "vals":[V_1, V_2, ... V_10]}
# Where I is the index of the selected video (0-9) and vals is an array
# of the scores calculated for each of the top 10 videos

def clicked():
    state = request.get_json()
    rl_network.ai_step(state)
    return Response(json.dumps(rl_network.weights))

def process_transcript(transcript,timescore):
    idx = 0
    # Transcripts on YouTube come in very rough chunks, based on a start time and 'duration'.
    # It's simply too rough for us to get a good feel for what the user is trying to listen for.
    #
    # This list comprehension below breaks up each of those chunks into an individual timestamp per word based on the duration and number of words.
    duration_segmented = [(y[1], chunk['start']+y[0]*(chunk['duration']/(chunk['text'].count(' ')+1))) for chunk in transcript for y in list(enumerate(chunk['text'].split(' ')))] 
    scored_transcript = []
    for time in timescore: # This is sorted from 0 - end, with only maybe marginal overlap
        start = time[0]
        end = time[1]
        score = time[2]
        
        chunk_str = ''
        #Now we're chunking up those words based on the time range the user actually watched/listened for, and scoring that more useful chunking o' words.
        for i in range(0,len(duration_segmented)):
            if(duration_segmented[i][1] > end):
                break
            elif(duration_segmented[i][1] > start):
                chunk_str += duration_segmented[i][0] + " "

        scored_transcript.append((chunk_str[:-1], score))

    return scored_transcript

        
def suggest_next_video(original_id, input_chunks, search_term):
    if(search_term == ''):
        global last_search
        search_term = last_search
    
	# This video_id is just a test case
    #if (original_id == 'R9npBuS9AsE'):
    #    output_id_list = get_canned_search_results()
    #else:

    output_video_list = query_video_ids(search_term)
    
    output_name_map = dict(output_video_list)
    output_id_list = [video[0] for video in output_video_list]
    
    #Truncate possible video list to 20 for performance reasons
    try:
        output_id_list.remove(original_id)
    except:
        pass
    output_id_list = output_id_list[:20]
        
    chunk_lookup_dict = {}
    
    chunk_counter = 0
    output_chunks = []
    for video_id in output_id_list:
        transcript_counter = 0
        try:
            output_video_list = yttapi.get_transcript(str(video_id))
        except yttapi.CouldNotRetrieveTranscript:
            continue
        
        video_length = len(output_video_list)
    
        for i in range(video_length//10):
            chunk_text_list = []
            for j in range(10):
                try:
                    chunk_text_list.append(output_video_list[transcript_counter]['text'])
                except Exception:
                    break
                chunk_text = ' '.join(chunk_text_list)
                transcript_counter += 1
                
            output_chunks.append(chunk_text)
            chunk_lookup_dict[chunk_counter] = video_id
            chunk_counter += 1
            

	# Exclude common stop words and those used frequently in YouTube transcripts
    my_stop_words = STOPWORDS.union(set(['[Music]', '[music]', '[Applause]', 'subscribe', 'channel', 'youtube']))
    #stoplist = set('for a of the and to in [music]'.split())
    texts = [
        [word for word in document.lower().split() if word not in my_stop_words]
        for document in output_chunks
    ]
    
    dictionary = corpora.Dictionary(texts)
    
    corpus = [dictionary.doc2bow(text) for text in texts]
    lsi = models.LsiModel(corpus, id2word=dictionary, num_topics=10)
    
    # generates an index of the corpus, need only do this once 
    index = similarities.MatrixSimilarity(lsi[corpus])
    
    
    video_average_score = {}
    for video_id in output_id_list:
        video_average_score[video_id] = []
    
    
    # Go through each input chunk and get an average score for each video
    for i in range(len(input_chunks)):
        
        # Skip over chunks the user didn't watch
        watched_score = input_chunks[i][1]
        if (watched_score == 0):
            continue
        
        doc=input_chunks[i][0]
        #doc=input_chunks[0][0]
        vec_bow = dictionary.doc2bow(doc.lower().split())
        vec_lsi = lsi[vec_bow]
        similarity_score = index[vec_lsi]
    
    
        # sorts based on descending relevance (earlier sort order = more useful)
        similarity_scores = sorted(enumerate(similarity_score), key=lambda item: -item[1])
        
        #chunk_ranking = [(documents[x],y) for (x,y) in similarity_scores]
        
        video_total_score = {}
        video_chunk_counts = {}
    
        
        for video_id in output_id_list:
            video_total_score[video_id] = 0
            video_chunk_counts[video_id] = 0  
            
            
        for chunk_id, score in similarity_scores:
            video_total_score[chunk_lookup_dict[chunk_id]] += score
            video_chunk_counts[chunk_lookup_dict[chunk_id]] += 1
            
        # Multiply the similarity ranking by the 'score' given to us that represents how slowly they 
        # watched the video chunk and how many times they repeated it
        # We append this to a list of average scores for the video
        for video_id in output_id_list:
            if (video_chunk_counts[video_id] == 0):
                video_average_score[video_id].append(0)
            else:
                avg_score = video_total_score[video_id]/video_chunk_counts[video_id]
                video_average_score[video_id].append(avg_score)
    
    
    video_sum = {}
    for idx, video_id in enumerate(video_average_score.keys()):
        total_score = sum(x for x in video_average_score[video_id])
        #video_sum[video_id] = (total_score * (1 + RL_WEIGHT_FACTOR * rl_network.weights['param_' + str(idx)]), output_name_map[video_id])
        video_sum[video_id] = (total_score, output_name_map[video_id])

    sorted_videos = list(sorted(video_sum.items(), key=lambda kv: -kv[1][0]))

    # now apply geva
    return_videos = []
    for i in range(0,10):
        return_videos.append((sorted_videos[i][0], (sorted_videos[i][1][0]* (1.0+RL_WEIGHT_FACTOR * rl_network.weights['param_'+str(i)]),sorted_videos[i][1][1])))

    return return_videos

## This is a test case only - not called in live demo
# Now deprecated for new search format w/ Video Title
def get_canned_search_results():
    
    output_id_list = [
                  # General tiny house videos
                  '4yanopKcmUw', '9mCi5ByAsRw', 'DoeEwBJJ5u8',
                  'xDnT28Ie1BY', 'KDdkHLJm31Q', '6F-9zmOU5zE',
                  'lnewtgCovFs', 'ZtsLtsYJLmc',
                  # TRAILERS
                  'LTVYIA0l_RA', 'Raonw6HcrVQ', 'Kj1JRprHj0g',
                  # FRAMING:
                  '7cPLuUVBXdM', 'K0ba7YRrITw',  'VXhqHIHDQHI',
                  # BATHROOM
                  'S7mC_dxRkM8', 'BY6_LxauYT0', 
                  # PLUMBING / TOILET
                  'loGKLy1gPmg', 'vM71d8wMuUU',
                  # CABINETS:
                  'jEPgETbfo2E',
                  # ELECTRIC:
                  'Vj8DoDcAmLU',
                  # FLOORING
                  'anxgS132OP4',
                  # INSULATING
                  'bn3hYEbQeAk', 'LP9TUFpM1r0', 'XIGUfa-X8Qo',
                  # ROOF
                  'wH250tJcX-8', 
                  # 'vdmhEyxGYz0',
                  # SIDING:
                  'rMH7zm4eCog', '18Pv9SOTyfY', 'bfIABQedZVg',
                  # STORAGE:
                  '2QIRFNnvBr8',
                  #OTHER
                  'fNk_zzaMoSs', # linear algebra
                  'R2JsjJyr0ck', # logarithmic functions
                  'a8GDpzZcC9Y', # basic ballet
                  'nM9f0W2KD5s', # Peter Thiel interview
                  'mCZwFFrvqz4', # wedding cake
                  '8mIGGn3AS1E'] # sew button
            
    return output_id_list

def query_video_ids(query,page=1):
    url = 'https://www.youtube.com/results?q=' + query
    if(page > 1):
        url += '&page=' + str(page)

    r = requests.get(url)
    if(r.status_code == 200):
        content = BeautifulSoup(r.content,'html.parser')
        return [(item.find('a')['href'][-11:], item.select('.yt-lockup-title')[0].find('a')['title']) for item in content.select('.yt-lockup-dismissable')]
        # returns a tuple of: (video_id, video_title)

    print("Error getting videoids " + r.status_code)
    print(r.content)

#video_id = 'R9npBuS9AsE'
# Building A Tiny House From Start To Finish!


#search_term = 'tiny house'
#ranked_suggestions = suggest_next_video(video_id, input_chunks, search_term, canned_search)
