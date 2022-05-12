# Video_Streaming
Objectives:

*We will implement a streaming video server and client that communicate using the Real-Time Streaming.

*Protocol (RTSP) and send data using the Real-time Transfer Protocol (RTP).

Requirement:

We will provide you code that implements the RTSP protocol in the server, the RTP de-packetization in the client, and takes care of simply displaying the
transmitted video.

Run:

*To run Server, firstly we command: python Server.py <server_port> , where <server_port>
represents for port that client can listen to. In this project we should make the value bigger than 1024. We choose 2000.

*After that we run Client, we command: python ClientLauncher.py <server_host> <server_port>
<RTP_port> <video_file> , where <server_host> is your IP address of your computer,
<server_port> is initialize in step run Server, <RTP_port> where the RTP packets are received,
<video_file> is name of video file.

<p align="center">
  <a <img src=""/> </a>

