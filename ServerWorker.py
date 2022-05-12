import random, math
import time
from random import randint
import sys, traceback, threading, socket, os

from VideoStream import VideoStream
from RtpPacket import RtpPacket

class ServerWorker:
	SETUP = 'SETUP'
	PLAY = 'PLAY'
	PAUSE = 'PAUSE'
	FORWARD = 'FORWARD'
	BACKWARD = 'BACKWARD'
	TEARDOWN = 'TEARDOWN'    
	DESCRIBE = 'DESCRIBE'   
	SWITCH = 'SWITCH'
	

	INIT = 0
	READY = 1
	PLAYING = 2
	state = INIT

	OK_200 = 0
	FILE_NOT_FOUND_404 = 1
	CON_ERR_500 = 2

	clientInfo = {}	
	forward = 0 
	backward = 0

	def __init__(self, clientInfo):
		self.clientInfo = clientInfo

	def run(self):
		threading.Thread(target=self.recvRtspRequest).start()

	def recvRtspRequest(self):
		"""Receive RTSP request from the client."""
		connSocket = self.clientInfo['rtspSocket'][0]
		while True:
			data = connSocket.recv(256)
			if data:
				print("Data received:\n" + data.decode("utf-8"))
				self.processRtspRequest(data.decode("utf-8"))

	def getAllMediaFiles(self):
        # Return a list of name of videos type Mjpeg or mjpeg
		fileList = []
		filenames = ""
		for file in os.listdir("./"):
			if file.endswith(".mjpeg") or file.endswith(".Mjpeg"):
				fileList.append(file)
		for filename in range(len(fileList)):
			filenames += (' ' + fileList[filename])
		return filenames

	def processRtspRequest(self, data):
		"""Process RTSP request sent from the client."""
		# Get the request type
		request = data.split('\n')
		line1 = request[0].split(' ')
		requestType = line1[0]

		# Get the media file name
		filename = line1[1]

		# Get the RTSP sequence number
		seq = request[1].split(' ')

		# Process SETUP request
		if requestType == self.SETUP:
			if self.state == self.INIT:
				# Update state
				print ("processing SETUP\n")
				try:
					self.clientInfo['videoStream'] = VideoStream(filename)
					self.state = self.READY
					self.clientInfo['videoStream'].calTotalTime()            
					self.totalTime = self.clientInfo['videoStream'].totalTime                
					self.fps = self.clientInfo['videoStream'].fps 
					self.noFrames = self.clientInfo['videoStream'].numFrames

				except IOError:
					self.replyRtsp(self.FILE_NOT_FOUND_404, seq[1])

				# Generate a randomized RTSP session ID
				self.clientInfo['session'] = randint(100000, 999999)

				# Send RTSP reply
				self.replyRtsp(self.OK_200, seq[1])
				#print ("sequenceNum is " + seq[1])

				# Get the RTP/UDP port from the last line
				self.clientInfo['rtpPort'] = request[2].split(' ')[3]
				print ("\nrtpPort is :" + self.clientInfo['rtpPort'])
				print ("filename is " + filename)

		# Process PLAY request
		elif requestType == self.PLAY:
			if self.state == self.READY:
				print ("processing PLAY\n" )
				self.state = self.PLAYING

				# Create a new socket for RTP/UDP
				self.clientInfo["rtpSocket"] = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

				self.replyRtsp(self.OK_200, seq[1])
				#print ('-'*60 + "\nSequence Number ("+ seq[1] + ")\nReplied to client\n" + '-'*60)

				# Create a new thread and start sending RTP packets
				self.clientInfo['event'] = threading.Event()
				self.clientInfo['worker']= threading.Thread(target=self.sendRtp)
				self.clientInfo['worker'].start()


		# Process PAUSE request
		elif requestType == self.PAUSE:
			if self.state == self.PLAYING:
				print ("processing PAUSE\n" )
				self.state = self.READY

				self.clientInfo['event'].set()

				self.replyRtsp(self.OK_200, seq[1])

		# Process FORWARD request      
		elif requestType == self.FORWARD:           
			if self.state == self.PLAYING:  
				print("processing FORWARD\n")
				self.state = self.PLAYING
				self.forward = 1
				self.replyRtsp(self.OK_200, seq[1])

        # Process BACKWARD request
		elif requestType == self.BACKWARD:
			if self.state == self.PLAYING:
				print("processing BACKWARD\n")
				self.state = self.PLAYING
				self.backward = 1
				self.replyRtsp(self.OK_200, seq[1])


		# Process TEARDOWN request
		elif requestType == self.TEARDOWN:
			print ("processing TEARDOWN \n")

			self.clientInfo['event'].set()

			self.replyRtsp(self.OK_200, seq[1])

			# Close the RTP socket
			self.clientInfo['rtpSocket'].close()

		# Process DESCRIBE request
		elif requestType == self.DESCRIBE:
			if not self.state == self.INIT:
				print("processing DESCRIBE\n")							
				self.replyRtsp(self.OK_200, seq[1], req = 'DESCRIBE', file = filename)

		# Process SWITCH request
		elif requestType == self.SWITCH:
			print("processing SWITCH\n")
            # Required the user to pause the video to switch
			if self.state == self.READY:
				self.clientInfo['videoStream'] = VideoStream(filename)
				self.clientInfo['videoStream'].calTotalTime()
				self.totalTime = self.clientInfo['videoStream'].totalTime
				self.fps = self.clientInfo['videoStream'].fps
				self.noFrames = self.clientInfo['videoStream'].numFrames
				self.replyRtsp(self.OK_200, seq[1])


	def sendRtp(self):
		"""Send RTP packets over UDP."""
		while True:
			self.clientInfo['event'].wait(0.05) 
			
			# Stop sending if request is PAUSE or TEARDOWN
			if self.clientInfo['event'].isSet(): 
				break 
				
			data = self.clientInfo['videoStream'].nextFrame(self.forward, self.backward)
			if (self.backward == 1): self.backward = 0
			if (self.forward == 1): self.forward = 0
			if data: 
				frameNumber = self.clientInfo['videoStream'].frameNbr()
				try:
					address = self.clientInfo['rtspSocket'][1][0]
					port = int(self.clientInfo['rtpPort'])
					self.clientInfo['rtpSocket'].sendto(self.makeRtp(data, frameNumber),(address,port))
				except:
					print("Connection Error")

	def makeRtp(self, payload, frameNbr):
		"""RTP-packetize the video data."""
		version = 2
		padding = 0
		extension = 0
		cc = 0
		marker = 0
		pt = 26 # MJPEG type
		seqnum = frameNbr
		ssrc = 0

		rtpPacket = RtpPacket()

		rtpPacket.encode(version, padding, extension, cc, seqnum, marker, pt, ssrc, payload)

		return rtpPacket.getPacket()

	def replyRtsp(self, code, seq, req = '', file = ''):
		"""Send RTSP reply to the client."""
		if code == self.OK_200:
			if req == 'DESCRIBE':
				sessionInfo =  '\nversion = 2' 
				sessionInfo += '\nsession = ' + str(self.clientInfo['session']) 
				sessionInfo += '\nserver addres = ' + str(self.clientInfo['rtspSocket'][1][0])  
				sessionInfo += '\ntype = Video ' + file + ' RTP/Mjpeg'
				sessionInfo += '\na = Encode utf-8'
				sessionInfo += '\nsize =  ' + str(self.clientInfo['videoStream'].getSize()) + ' Bytes' 				

				reply = 'RTSP/1.0 200 OK\nCSeq: ' + seq + '\nSession: ' + str(self.clientInfo['session']) + '\nTotal time: ' + \
                    str(self.totalTime) + '\nMean FPS: ' + str(self.fps) + '\nTotal frames: ' + str(self.noFrames)
				reply += '\nFrom server port: ' + str(self.clientInfo['rtspSocket'][1][1])
				reply += '\nContent-Length: {}\n'.format(str(len(sessionInfo))) 
				reply += sessionInfo

				connSocket = self.clientInfo['rtspSocket'][0]
				connSocket.send(reply.encode())
			else:
				reply = 'RTSP/1.0 200 OK\nCSeq: ' + seq + '\nSession: ' + str(self.clientInfo['session']) + '\nTotal time: ' + \
                    str(self.totalTime) + '\nMean FPS: ' + str(self.fps) + '\nTotal frames: ' + str(self.noFrames) + \
                    '\nMedia:' + self.getAllMediaFiles()
				connSocket = self.clientInfo['rtspSocket'][0]
				connSocket.send(reply.encode())

		# Error messages
		elif code == self.FILE_NOT_FOUND_404:
			print ("404 NOT FOUND")
		elif code == self.CON_ERR_500:
			print ("500 CONNECTION ERROR")
