// ==UserScript==
// @name         YouTube Watch Monitor
// @namespace    http://tampermonkey.net/
// @version      0.1
// @description  Monitors the timestamps and amount you actually were watching something in to an array.
// @author       Jagged Edge
// @match        https://www.tampermonkey.net/faq.php?version=4.8.41&ext=dhdg&updated=true
// @include      http*://*.youtube.com/*
// @include      http*://youtube.com/*
// @include      http*://*.youtu.be/*
// @include      http*://youtu.be/*
// @grant       GM_xmlhttpRequest
// ==/UserScript==

(function() {
    'use strict';
    const suggestedCount = 10;

    var lastStart = 0.0;
    var lastEnd = 0.0;
    var duration = 0.0;
    var lastRate = 1.0;
    var player = document.getElementsByTagName('video')[0];
    var search = document.getElementsByTagName('ytd-search')[0];
    var watchedMetric = [];
    var videoId = '';

    var query = '';
    var attached = false;

    var hasPlayed = false;
    var hasSearched = false;

    function updateTimescore(){
        var postObj = new Object();
        postObj.video_id = videoId;
        postObj.timescore = watchedMetric;
        postObj.query = query;
        console.log(postObj);
        GM_xmlhttpRequest ( {
            method:     "POST",
            url:        "http://127.0.0.1:5000/watch-data",
            data:       JSON.stringify ( postObj ),
            headers:    {
                "Content-Type": "application/json",
            },
            onload:     function (response) {
                gotTopResults(JSON.parse(response.responseText));
            },
            onerror:    function(reponse) {
                //alert('error');
                console.log("error: ", reponse);
            }
        } );
    }

    function gotTopResults(videos){
        var relatedDiv = document.getElementsByTagName('ytd-watch-next-secondary-results-renderer')[0].children.items.getElementsByTagName('ytd-compact-video-renderer');
        if(relatedDiv){
            for(var i = 0; i < videos.length; i++){
                generateThumbnail(videos[i],i,relatedDiv);
            }
        }
    }

    function generateThumbnail(video, index, relatedDiv){
        relatedDiv[index].children[0].children[0].children[0].href = '/watch?v=' + video[0];
        relatedDiv[index].children[0].children[0].children[0].children[0].children[0].src = 'https://i.ytimg.com/vi/' + video[0] + '/hqdefault.jpg'
        relatedDiv[index].children[0].children[1].children[0].href = '/watch?v=' + video[0];
        relatedDiv[index].children[0].children[1].children[0].children[0].children[1].textContent = video[1][1];
        relatedDiv[index].children[0].children[1].children[0].children[1].children[0].children[0].children[0].children[0].children[0].children[0].textContent = 'Score: ' + video[1][0];
        relatedDiv[index].children[0].children[1].children[0].children[1].children[0].children[1].children[0].textContent = 'Suggested for your learning';
    }

    function initData(){
        duration = player.duration;
        watchedMetric = [[0.0,player.duration,0.0]];
        lastRate = player.playbackRate; // may be defaulted to something other than 1.0

        videoId = window.location.href.match(/(?:https?:\/{2})?(?:w{3}\.)?youtu(?:be)?\.(?:com|be)(?:\/watch\?v=|\/)([^\s&]+)/)[1]; // gets YT video id from URL
    }

    function onSeek(){
        if(hasPlayed){
            markTimeWidth(lastStart,lastEnd,lastRate);
        }
        hasPlayed = false;
        lastStart = player.currentTime;
        lastEnd = player.currentTime;
    }

    function onPause(){
        lastEnd = player.currentTime;
        markTimeWidth(lastStart,lastEnd,lastRate);
        lastStart = player.currentTime;
        updateTimescore();
    }

    function onTime(){
        if(!player.paused){
            hasPlayed = true;
            lastEnd = player.currentTime;
        }
    }

    function onRateChange(){
        markTimeWidth(lastStart,player.currentTime,lastRate);
        lastRate = player.playbackRate;
        lastStart = player.currentTime;
        lastEnd = player.currentTime;
    }
    function onEnded(){
        markTimeWidth(lastStart, duration, lastRate);
    }

    function markTimeWidth(start,end,playrate){
        if(playrate == 0 || end-start < Math.abs(0.25)){
            return;
        }
        var startIdx = 0;
        var endIdx = 0;
        var fStart = false;

        var newMetric = [];

        for(var i = 0; i < watchedMetric.length; i++){
            if(watchedMetric[i][0] <= start){ // found first index that represents time range
                startIdx = i;
                fStart = true;
            }
            if(watchedMetric[i][1] >= end){ // found last index that represents time range
                endIdx = i;
                break;
            }
        }
        for(i=0; i < startIdx; i++){
            newMetric.push(watchedMetric[i]);
        }

        var score = 1.0/playrate;

        if(watchedMetric[startIdx][0]<start) {
            newMetric.push([watchedMetric[startIdx][0],start,watchedMetric[startIdx][2]]);
            watchedMetric[startIdx][0]=start;// fix start index to its new end
        }
       // newMetric[startIdx] = [watchedMetric[startIdx][0],start,watchedMetric[startIdx][2]];
        var offset = 0;
        for(i = startIdx; i <= endIdx; i++){
            newMetric.push([watchedMetric[i][0], watchedMetric[i][1], watchedMetric[i][2]+score]); // add new score
        }
        if(watchedMetric[endIdx][1]>=end){
            newMetric[newMetric.length-1][1] = end;
            newMetric.push([end,watchedMetric[endIdx][1],watchedMetric[endIdx][2]]); // fix end index to its new start
        }
        for(i = endIdx+1; i <= watchedMetric.length-1; i++){
            newMetric.push(watchedMetric[i]);
        }

        watchedMetric = newMetric;

        console.log(watchedMetric);
    }

    function youtube_parser(url){
        var regExp = /^.*((youtu.be\/)|(v\/)|(\/u\/\w\/)|(embed\/)|(watch\?))\??v?=?([^#\&\?]*).*/;
        var match = url.match(regExp);
        return (match&&match[7].length==11)? match[7] : false;
    }

    function attach(){
        player = document.getElementsByTagName('video')[0];
        search = document.getElementsByTagName('ytd-search')[0];
        if(player && player.src != ''){
            query = document.getElementsByTagName('input').search;
            if(query){
                query = query.value;
                if(query != ""){
                    console.log(query);
                    hasSearched = false;
                }
            }
            player.addEventListener('seeking',onSeek,false); // 'seeking' event actually occurs on seek -- not while the user is scrolling the seek bar. 'seeked' appears too late relative to 'timeupdate' event.
            player.addEventListener('timeupdate',onTime,false);
            player.addEventListener('ratechange',onRateChange,false);
            player.addEventListener('ended',onEnded,false);
            player.addEventListener('pause',onPause,false);
            if(player.readyState > 0){
                lastEnd = 0.0;
                initData();
            }else{
                player.addEventListener('loadedmetadata',initData,false);
            }
        }
    }
    if(player){
        attach();
    }
    document.addEventListener('yt-navigate-finish', (event) => {attach();});
    //document.addEventListener('transitionend', (event) => {attach();});

})();