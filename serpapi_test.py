import os
import sys
from serpapi import GoogleSearch
from urllib.parse import urlparse
import json
from bs4 import BeautifulSoup
import requests
import re
import uuid
from configparser import ConfigParser


def getTimeInSeconds(t):
    s = 0
    if len(t) == 2:
        s += int(t[0]) * 60 + int(t[1])
    else:
        s += int(t[0]) * 3600 + int(t[1]) * 60 + int(t[2])
    return s


def getHTMLdocument(url):
    # request for HTML document of given url
    response = requests.get(url)
    # response will be provided in JSON format
    return response.text


def extractResults(dict, soup):
    social_media_list = []
    webpage_list = []
    count = 0
    organic_results = dict['organic_results']
    for ele in organic_results:
        link = urlparse(ele['link'])
        domain = link.netloc.split('.')[-2]

        web = link.scheme + "://" + link.netloc
        title = ele['title']
        url = ele['link']
        if domain in ['twitter', 'facebook', 'linkedin', 'reddit', 'instagram']:
            social_media_list.append({"Website": web, "results": [{"Title": title, "URL": url}]})
            count += 1
        else:
            webpage_list.append({"Website": web, "results": [{"Title": title, "URL": url}]})

    if 'twitter_results' in dict:  # uses BeautifulSoup to find title of twitter profile links as api doesn't provide
        title = ""
        headerlist = soup.find_all(re.compile('^h[3]'))
        for header in headerlist:
            if "Twitter" in header.text:
                title = header.text
        url = dict['twitter_results']['link']
        social_media_list.append({"Website": "https://twitter.com", "results": [{"Title": title, "URL": url}]})
        count += 1
    return count, social_media_list, webpage_list


def extractVideos(dict, soup):
    video_list = []
    count = 0
    if "inline_videos" in dict:
        video_results = dict['inline_videos']
        for ele in video_results:
            if 'duration' in ele.keys():
                seconds = getTimeInSeconds(ele['duration'].split(':'))
            else:
                seconds = "N/A"
            count += 1
            link = urlparse(ele['link'])
            web = link.scheme + "://" + link.netloc
            video_list.append({"Website": web, "results": [
                {"DurationInSeconds": seconds, "Title": ele['title'], "URL": ele['link']}]})
    # using BeautifulSoup to find youtube video strip data as api can't find (example - searching "naval")
    vid_info = soup.find_all("a", {"class": "irqWwf"})
    vid_title = soup.find_all("div", {"class": "w18VHb YVgRyb tNxQIb ynAwRc OSrXXb"})
    for i in range(len(vid_info)):
        link = vid_info[i].get('href')
        time = vid_info[i].text.split(':')
        time[-1] = time[-1][0:2]
        seconds = getTimeInSeconds(time)
        title = vid_title[i].text
        count += 1
        video_list.append({"Website": "https://www.youtube.com/", "results": [
            {"DurationInSeconds": seconds, "Title": title, "URL": link}]})
    return count, video_list


file = 'config.ini'
config = ConfigParser()
config.read(file)
try:
    resultsPerPage = config['params']['resultsPerPage']
except:
    resultsPerPage = "10"
    print("No config file")

params = {
    "api_key": "a11053c20c599f6b9b124a3638bb41c8ec9835fc0963be2377e6f9f65bfdec18",
    "engine": "google",
    "q": sys.argv[1],
    "num": resultsPerPage,
    "google_domain": "google.com",
    "gl": "us",
    "hl": "en",

}

search = GoogleSearch(params)
api_response = search.get_dict()

url_to_scrape = api_response['search_metadata']['raw_html_file']
print(url_to_scrape)

# create document and create soap object
html_document = getHTMLdocument(url_to_scrape)
soup = BeautifulSoup(html_document, 'html.parser')

# Uncomment lines 120-121 to save the json returned from the api
# with open('api_results_json.json', 'w') as f:
#     json.dump(api_response, f, indent=4, separators=(',', ': '))

social_media_count, social_media_list, webpage_list = extractResults(api_response, soup)
video_count, video_list = extractVideos(api_response, soup)

final = {"q": api_response['search_information']['query_displayed'],
         "timeTakenInMs": int(api_response['search_information']["time_taken_displayed"] * 1000),
         "pageOneResultCount": int(resultsPerPage), "pageOneVideoResultCount": video_count,
         "pageOneSocialMediaResultCount": social_media_count, "results": {}}
final["results"]["Social Media"] = social_media_list
final["results"]["Webpages"] = webpage_list
final["results"]["Videos"] = video_list

if not os.path.exists('database'):
    os.makedirs('database')
file_path = os.path.dirname(os.path.realpath(__file__)) + '/database/' + str(uuid.uuid4()) + ".json"
with open(file_path, 'w') as f:
    json.dump(final, f, indent=4, separators=(',', ': '))
