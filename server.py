from flask import Flask, request, Response
from youtube_transcript_api import YouTubeTranscriptApi as yttapi

import json

from gensim import models, corpora,similarities
from gensim.parsing.preprocessing import STOPWORDS

import requests

app = Flask(__name__)

last_search = ''

@app.route('/watch-data',methods=['POST'])
def watch_data():
    global last_search
    req_data = request.get_json()

    video_id = req_data['video_id']
    timescore = req_data['timescore']
    search = req_data['query']

    transcript = yttapi.get_transcript(video_id)

    scored_transcript = process_transcript(transcript,timescore)
    
    
    return Response(json.dumps(suggest_next_video(video_id,scored_transcript,search)),mimetype='application/json')

@app.route('/searched',methods=['POST'])
def searched():
    global last_search
    req_data = request.get_json()
    last_search = req_data['query']

def process_transcript(transcript,timescore):
    idx = 0
    duration_segmented = [(y[1], chunk['start']+y[0]*(chunk['duration']/(chunk['text'].count(' ')+1))) for chunk in transcript for y in list(enumerate(chunk['text'].split(' ')))] 
    scored_transcript = []
    for time in timescore: # This is sorted from 0 - end, with only maybe marginal overlap
        start = time[0]
        end = time[1]
        score = time[2]
        
        chunk_str = ''
        for i in range(0,len(duration_segmented)):
            if(duration_segmented[i][1] > end):
                break
            elif(duration_segmented[i][1] > start):
                chunk_str += duration_segmented[i][0] + " "

        scored_transcript.append((chunk_str[:-1], score))

    return scored_transcript

        
def suggest_next_video(video_id, input_chunks, search_term):

	# This video_id is just a test case
    if (video_id == 'R9npBuS9AsE'):
        output_id_list = get_canned_search_results()
    else:
        output_id_list = get_real_search_results(video_id,search_term)
    
    #Truncate possible video list to 20 for performance reasons
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
    
    # I am making up the number 10, example used 2
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
    for video_id in video_average_score.keys():
        total_score = sum(x for x in video_average_score[video_id])
        video_sum[video_id] = total_score
    
    
    sorted_videos = sorted(video_sum.items(), key=lambda kv: -kv[1])
    
    return sorted_videos

# This is a test case only - not called in live demo
def get_canned_search_results():
    
    # Canned results for demo
    
    """
    output_id_list = [
                  '4yanopKcmUw', '9mCi5ByAsRw', 'DoeEwBJJ5u8',
                  'xDnT28Ie1BY', 'KDdkHLJm31Q', '6F-9zmOU5zE',
                  'fNk_zzaMoSs', # linear algebra
                  'R2JsjJyr0ck', # logarithmic functions
                  'a8GDpzZcC9Y', # basic ballet
                  'nM9f0W2KD5s', # Peter Thiel interview
                  'mCZwFFrvqz4', # wedding cake
                  '8mIGGn3AS1E'] # sew button
    """
    
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


# This is called in the live demo
def get_real_search_results(original_video,search_term):
    

    search_words = search_term.split(' ')
    
    search_term = '%20'.join(search_words)
    #max_results = 20
    
    output_id_list = []
    

    url = 'http://youtube-scrape.herokuapp.com/api/search?q=' + str(search_term)

    request_results = requests.get(url, timeout=40)
    
    result_json = request_results.json()
    
    try:
        items = result_json['results']
        items = items[:20]
    except Exception as e:
        print ("ERROR: " + str(e))
        return None
   

    for item in items:
        try:
            video_id = item['video']['id']
            output_id_list.append(str(video_id))
        except KeyError:
            continue
        
    return output_id_list
    

#video_id = 'R9npBuS9AsE'
# Building A Tiny House From Start To Finish!


#search_term = 'tiny house'
#ranked_suggestions = suggest_next_video(video_id, input_chunks, search_term, canned_search)
