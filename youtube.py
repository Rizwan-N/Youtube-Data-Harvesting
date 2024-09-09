from googleapiclient.discovery import build
import pymongo
import psycopg2
import pandas as pd
import streamlit as st

#API key connection

def Api_connect():
    Api_Id="AIzaSyCgYneO7rLAxQhDDRX-mSEBgSopv3HbPjs"
    api_service_name="youtube"
    api_version="V3"

    youtube=build(api_service_name,api_version,developerKey=Api_Id)

    return youtube

youtube=Api_connect()

#Get Channel Information

def get_channel_info(channel_id):
    request=youtube.channels().list(
                    part="snippet,contentDetails,statistics",
                    id=channel_id
    )
    response=request.execute()

    for i in response['items']:
        data=dict(Channel_Name=i["snippet"]["title"],
                Channel_Id=i["id"],
                Subscribers=i['statistics']['subscriberCount'],
                Views=i["statistics"]["viewCount"],
                Total_Videos=i["statistics"]["videoCount"],
                Channel_Description=i["snippet"]["description"],
                Playlist_Id=i["contentDetails"]["relatedPlaylists"]["uploads"])
    return data

#Get Video Ids

def get_videos_ids(channel_id):
    video_ids=[]
    response=youtube.channels().list(id=channel_id, 
                                    part='contentDetails').execute()
    Playlist_Id=response['items'][0]['contentDetails']['relatedPlaylists']['uploads']

    next_page_token=None

    while True:

        response1=youtube.playlistItems().list(
                                            part='snippet',
                                            playlistId=Playlist_Id,
                                            maxResults=50,
                                            pageToken=next_page_token).execute()
        for i in range(len(response1['items'])):
            video_ids.append(response1['items'][i]['snippet']['resourceId']['videoId'])
        next_page_token=response1.get('nextPageToken')

        if next_page_token is None:
            break
    return video_ids

#Get Video information

def get_video_info(video_ids):
    video_data=[]
    for video_id in video_ids:
        request=youtube.videos().list(
            part="snippet,contentDetails,statistics",
            id=video_id
        )
        response=request.execute()

        for item in response["items"]:
            data=dict(Channel_Name=item['snippet']['channelTitle'],
                    Channel_Id=item['snippet']['channelId'],
                    Video_Id=item['id'],
                    Title=item['snippet']['title'],
                    Tags=item['snippet'].get('tags'),
                    Thumbnail=item['snippet']['thumbnails']['default']['url'],
                    Description=item['snippet'].get('description'),
                    Published_Date=item['snippet']['publishedAt'],
                    Duration=item['contentDetails']['duration'],
                    Views=item['statistics'].get('viewCount'),
                    Likes=item['statistics'].get('likeCount'),
                    Comments=item['statistics'].get('commentCount'),
                    Favorite_Count=item['statistics']['favoriteCount'],
                    Definition=item['contentDetails']['definition'],
                    Caption_Status=item['contentDetails']['caption']
                    )
            video_data.append(data)
    return video_data

#Get Comment Information

def get_comment_info(video_ids):
    Comment_data=[]
    try:
        for video_id in video_ids:
            request=youtube.commentThreads().list(
                part="snippet",
                videoId=video_id,
                maxResults=50
                )
            response=request.execute()

            for item in response['items']:
                data=dict(Comment_Id=item['snippet']['topLevelComment']['id'],
                        Video_Id=item['snippet']['topLevelComment']['snippet']['videoId'],
                        Comment_Text=item['snippet']['topLevelComment']['snippet']['textDisplay'],
                        Comment_Author=item['snippet']['topLevelComment']['snippet']['authorDisplayName'],
                        Comment_Published=item['snippet']['topLevelComment']['snippet']['publishedAt'])
                
                Comment_data.append(data)
    except:
        pass
    return Comment_data

#Get Playlist Information

def get_playlist_details(channel_id):
        next_page_token=None
        All_data=[]

        while True:
                request=youtube.playlists().list(
                        part='snippet,contentDetails',
                        channelId=channel_id,
                        maxResults=50,
                        pageToken=next_page_token
                )
                response=request.execute()

                for item in response['items']:
                        data=dict(Playlist_Id=item['id'],
                                Title=item['snippet']['title'],
                                Channel_Id=item['snippet']['channelId'],
                                Channel_Name=item['snippet']['channelTitle'],
                                PublishedAt=item['snippet']['publishedAt'],
                                Video_Count=item['contentDetails']['itemCount'])
                        All_data.append(data)

                next_page_token=response.get('nextPageToken')
                if next_page_token is None:
                        break
        return All_data

#Upload to MongoDB

client=pymongo.MongoClient("mongodb+srv://rizwanhome46:rizwanan01@cluster0.p1us8el.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0")
db=client["Youtube_data"]

def channel_details(channel_id):
    ch_details=get_channel_info(channel_id)
    pl_details=get_playlist_details(channel_id)
    vi_ids=get_videos_ids(channel_id)
    vi_details=get_video_info(vi_ids)
    com_details=get_comment_info(vi_ids)

    coll1=db["channel_details"]
    coll1.insert_one({"channel_information":ch_details,"playlist_information":pl_details,
                      "video_information":vi_details,"comment_information":com_details})
    
    return "Upload Completed Successfully"

#Table creation for channels, playlists, videos, comments

def channels_table(channel_name_s):
    mydb=psycopg2.connect(host="localhost",
                        user="postgres",
                        password="rizwanan01",
                        database="youtube_data",
                        port="5432")
    cursor=mydb.cursor()

    create_query='''create table if not exists channels(Channel_Name varchar(100),
                                                        Channel_Id varchar(80) primary key,
                                                        Subscribers bigint,
                                                        Views bigint,
                                                        Total_Videos int,
                                                        Channel_Description text,
                                                        Playlist_Id varchar(80))'''
    cursor.execute(create_query)
    mydb.commit()

    single_channel_details=[]
    db=client["Youtube_data"]
    coll1=db["channel_details"]
    for ch_data in coll1.find({"channel_information.Channel_Name": channel_name_s},{"_id":0}):
        single_channel_details.append(ch_data["channel_information"])

    df_single_channel_details=pd.DataFrame(single_channel_details)


    for index,row in df_single_channel_details.iterrows():
        insert_query='''insert into channels(Channel_Name,
                                            Channel_Id,
                                            Subscribers,
                                            Views,
                                            Total_Videos,
                                            Channel_Description,
                                            Playlist_Id)
                                            
                                            values(%s,%s,%s,%s,%s,%s,%s)'''
        values=(row['Channel_Name'],
                row['Channel_Id'],
                row['Subscribers'],
                row['Views'],
                row['Total_Videos'],
                row['Channel_Description'],
                row['Playlist_Id'])
        
        try:
            cursor.execute(insert_query,values)
            mydb.commit()

        except:
            news= f"The Provided Channel Name {channel_name_s} Already Exists"
            return news

def playlist_table(channel_name_s):
    mydb=psycopg2.connect(host="localhost",
                        user="postgres",
                        password="rizwanan01",
                        database="youtube_data",
                        port="5432")
    cursor=mydb.cursor()

    create_query='''create table if not exists playlists(Playlist_Id varchar(100) primary key,
                                                        Title varchar(100),
                                                        Channel_Id varchar(100),
                                                        Channel_Name varchar(100),
                                                        PublishedAt timestamp,
                                                        Video_Count int)'''
    cursor.execute(create_query)
    mydb.commit()

    single_playlist_details=[]
    db=client["Youtube_data"]
    coll1=db["channel_details"]
    for ch_data in coll1.find({"channel_information.Channel_Name": channel_name_s},{"_id":0}):
        single_playlist_details.append(ch_data["playlist_information"])

    df_single_playlist_details=pd.DataFrame(single_playlist_details[0])

    for index,row in df_single_playlist_details.iterrows():
        insert_query='''insert into playlists(Playlist_Id,
                                            Title,
                                            Channel_Id,
                                            Channel_Name,
                                            PublishedAt,
                                            Video_Count)
                                            
                                            values(%s,%s,%s,%s,%s,%s)'''
        values=(row['Playlist_Id'],
                row['Title'],
                row['Channel_Id'],
                row['Channel_Name'],
                row['PublishedAt'],
                row['Video_Count'])
    
        cursor.execute(insert_query,values)
        mydb.commit()

def videos_table(channel_name_s):
    mydb=psycopg2.connect(host="localhost",
                        user="postgres",
                        password="rizwanan01",
                        database="youtube_data",
                        port="5432")
    cursor=mydb.cursor()

    create_query='''create table if not exists videos(Channel_Name varchar(100),
                                                    Channel_Id varchar(100),
                                                    Video_Id varchar(30) primary key,
                                                    Title varchar(150),
                                                    Tags text,
                                                    Thumbnail varchar(200),
                                                    Description text,
                                                    Published_Date timestamp,
                                                    Duration interval,
                                                    Views bigint,
                                                    Likes bigint,
                                                    Comments int,
                                                    Favorite_Count int,
                                                    Definition varchar(10),
                                                    Caption_Status varchar(50))'''
    cursor.execute(create_query)
    mydb.commit()

    single_video_details=[]
    db=client["Youtube_data"]
    coll1=db["channel_details"]
    for ch_data in coll1.find({"channel_information.Channel_Name": channel_name_s},{"_id":0}):
        single_video_details.append(ch_data["video_information"])

    df_single_video_details=pd.DataFrame(single_video_details[0])

    for index,row in df_single_video_details.iterrows():
        insert_query='''insert into videos(Channel_Name,
                                        Channel_Id,
                                        Video_Id,
                                        Title,
                                        Tags,
                                        Thumbnail,
                                        Description,
                                        Published_Date,
                                        Duration,
                                        Views,
                                        Likes,
                                        Comments,
                                        Favorite_Count,
                                        Definition,
                                        Caption_Status)
                                            
                                        values(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)'''
        values=(row['Channel_Name'],
                row['Channel_Id'],
                row['Video_Id'],
                row['Title'],
                row['Tags'],
                row['Thumbnail'],
                row['Description'],
                row['Published_Date'],
                row['Duration'],
                row['Views'],
                row['Likes'],
                row['Comments'],
                row['Favorite_Count'],
                row['Definition'],
                row['Caption_Status'])

        cursor.execute(insert_query,values)
        mydb.commit()

def comments_table(channel_name_s):
    mydb=psycopg2.connect(host="localhost",
                        user="postgres",
                        password="rizwanan01",
                        database="youtube_data",
                        port="5432")
    cursor=mydb.cursor()

    create_query='''create table if not exists comments(Comment_Id varchar(100) primary key,
                                                        Video_Id varchar(50),
                                                        Comment_Text text,
                                                        Comment_Author varchar(150),
                                                        Comment_Published timestamp)'''
    cursor.execute(create_query)
    mydb.commit()

    single_comment_details=[]
    db=client["Youtube_data"]
    coll1=db["channel_details"]
    for ch_data in coll1.find({"channel_information.Channel_Name": channel_name_s},{"_id":0}):
        single_comment_details.append(ch_data["comment_information"])

    df_single_comment_details=pd.DataFrame(single_comment_details[0])

    for index,row in df_single_comment_details.iterrows():
        insert_query='''insert into comments(Comment_Id,
                                            Video_Id,
                                            Comment_Text,
                                            Comment_Author,
                                            Comment_Published)
                                            
                                            values(%s,%s,%s,%s,%s)'''
        values=(row['Comment_Id'],
                row['Video_Id'],
                row['Comment_Text'],
                row['Comment_Author'],
                row['Comment_Published'])

        cursor.execute(insert_query,values)
        mydb.commit()

def tables(single_channel):
    news=channels_table(single_channel)
    if news:
        return news
    
    else:
        playlist_table(single_channel)
        videos_table(single_channel)
        comments_table(single_channel)

    return "Tables Created Successfully"

def show_channels_table():
    ch_list=[]
    db=client["Youtube_data"]
    coll1=db["channel_details"]
    for ch_data in coll1.find({},{"_id":0,"channel_information":1}):
        ch_list.append(ch_data["channel_information"])
    df=st.dataframe(ch_list)

    return df

def show_playlists_table():
    pl_list=[]
    db=client["Youtube_data"]
    coll1=db["channel_details"]
    for pl_data in coll1.find({},{"_id":0,"playlist_information":1}):
        for i in range(len(pl_data["playlist_information"])):
            pl_list.append(pl_data["playlist_information"][i])
    df1=st.dataframe(pl_list)

    return df1

def show_videos_table():
    vi_list=[]
    db=client["Youtube_data"]
    coll1=db["channel_details"]
    for vi_data in coll1.find({},{"_id":0,"video_information":1}):
        for i in range(len(vi_data["video_information"])):
            vi_list.append(vi_data["video_information"][i])
    df2=st.dataframe(vi_list)

    return df2

def show_comments_table():
    com_list=[]
    db=client["Youtube_data"]
    coll1=db["channel_details"]
    for com_data in coll1.find({},{"_id":0,"comment_information":1}):
        for i in range(len(com_data["comment_information"])):
            com_list.append(com_data["comment_information"][i])
    df3=st.dataframe(com_list)

    return df3

#Streamlit Part

with st.sidebar:
    st.title(":red[YOUTUBE DATA HARVESTING AND WAREHOUSING]")
    st.header("Skill Takeaway")
    st.caption("Python Scripting")
    st.caption("Data Collection")
    st.caption("MongoDB")
    st.caption("API Integration")
    st.caption("Data Management using MongoDB and SQL")

channel_id=st.text_input("Enter the channel ID")

if st.button("Collect and Store Data"):
    ch_ids=[]
    db=client["Youtube_data"]
    coll1=db["channel_details"]
    for ch_data in coll1.find({},{"_id":0,"channel_information":1}):
        ch_ids.append(ch_data["channel_information"]["Channel_Id"])

    if channel_id in ch_ids:
        st.success("Channel Details of the given channel id already exists")

    else:
        insert=channel_details(channel_id)
        st.success(insert)

all_channels=[]
db=client["Youtube_data"]
coll1=db["channel_details"]
for ch_data in coll1.find({},{"_id":0,"channel_information":1}):
    all_channels.append(ch_data["channel_information"]["Channel_Name"])

unique_channel=st.selectbox("Select the Channel",all_channels)

if st.button("Migrate to SQL"):
    Table=tables(unique_channel)
    st.success(Table)

show_table=st.radio("SELECT THE TABLE FOR VIEW",("CHANNELS","PLAYLISTS","VIDEOS","COMMENTS"))

if show_table=="CHANNELS":
    show_channels_table()

elif show_table=="PLAYLISTS":
    show_playlists_table()

elif show_table=="VIDEOS":
    show_videos_table()

elif show_table=="COMMENTS":
    show_comments_table()

#SQL Connection

mydb=psycopg2.connect(host="localhost",
                    user="postgres",
                    password="rizwanan01",
                    database="youtube_data",
                    port="5432")
cursor=mydb.cursor()

question=st.selectbox("Select your Question",("---None Selected---",
                                              "1. All the Videos and Channel Names",
                                              "2. Channels with most number of videos",
                                              "3. Top 10 Most Viewed Videos",
                                              "4. Comments in Each Videos",
                                              "5. Videos with highest Likes",
                                              "6. Likes of All Videos",
                                              "7. Views of All Channels",
                                              "8. Videos Published in the year of 2023",
                                              "9. Average Duration of all Videos in Each Channel",
                                              "10. Videos with highest number of Comments"))

if question=="1. All the Videos and Channel Names":
    query1='''select title as videos,channel_name as channelname from videos'''
    cursor.execute(query1)
    mydb.commit()
    t1=cursor.fetchall()
    df1=pd.DataFrame(t1,columns=["video title","channel name"])
    st.write(df1)

elif question=="2. Channels with most number of videos":
    query2='''select channel_name as channelname,total_videos as no_videos from channels order by total_videos desc'''
    cursor.execute(query2)
    mydb.commit()
    t2=cursor.fetchall()
    df2=pd.DataFrame(t2,columns=["channel name","No of Videos"])
    st.write(df2)

elif question=="3. Top 10 Most Viewed Videos":
    query3='''select views as views,channel_name as channelname,title as videotitle from videos where views is not null order by views desc limit 10'''
    cursor.execute(query3)
    mydb.commit()
    t3=cursor.fetchall()
    df3=pd.DataFrame(t3,columns=["views","channel name","videotitle"])
    st.write(df3)

elif question=="4. Comments in Each Videos":
    query4='''select comments as no_comments,title as videotitle from videos where comments is not null'''
    cursor.execute(query4)
    mydb.commit()
    t4=cursor.fetchall()
    df4=pd.DataFrame(t4,columns=["no of comments","videotitle"])
    st.write(df4)

elif question=="5. Videos with Highest Likes":
    query5='''select title as videotitle,channel_name as channelname,likes as likecount from videos where likes is not null order by likes desc'''
    cursor.execute(query5)
    mydb.commit()
    t5=cursor.fetchall()
    df5=pd.DataFrame(t5,columns=["videotitle","channelname","likecount"])
    st.write(df5)

elif question=="6. Likes of All Videos":
    query6='''select likes as likecount,title as videotitle from videos'''
    cursor.execute(query6)
    mydb.commit()
    t6=cursor.fetchall()
    df6=pd.DataFrame(t6,columns=["likecount","videotitle"])
    st.write(df6)

elif question=="7. Views of All Channels":
    query7='''select channel_name as channelname,views as totalviews from channels'''
    cursor.execute(query7)
    mydb.commit()
    t7=cursor.fetchall()
    df7=pd.DataFrame(t7,columns=["channelname","totalviews"])
    st.write(df7)

elif question=="8. Videos Published in the year of 2023":
    query8='''select title as video_title,published_date as videorelease,channel_name as channelname from videos where extract(year from published_date)=2023'''
    cursor.execute(query8)
    mydb.commit()
    t8=cursor.fetchall()
    df8=pd.DataFrame(t8,columns=["videotitle","published_date","channelname"])
    st.write(df8)

elif question=="9. Average Duration of all Videos in Each Channel":
    query9='''select channel_name as channelname,avg(duration) as averageduration from videos group by channel_name'''
    cursor.execute(query9)
    mydb.commit()
    t9=cursor.fetchall()
    df9=pd.DataFrame(t9,columns=["channelname","averageduration"])

    T9=[]
    for index,row in df9.iterrows():
        channel_title=row["channelname"]
        average_duration=row["averageduration"]
        average_duration_str=str(average_duration)
        T9.append(dict(channelname=channel_title,avgduration=average_duration_str))
    df=pd.DataFrame(T9)
    st.write(df)

elif question=="10. Videos with highest number of Comments":
    query10='''select title as videotitle,channel_name as channelname,comments as comments from videos where comments is not null order by comments desc'''
    cursor.execute(query10)
    mydb.commit()
    t10=cursor.fetchall()
    df10=pd.DataFrame(t10,columns=["videotitle","channelname","comments"])
    st.write(df10)