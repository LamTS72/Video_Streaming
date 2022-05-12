from tkinter import *
from tkinter import messagebox
from PIL import Image, ImageTk
import socket, threading, sys, traceback, os
import time

from RtpPacket import RtpPacket

CACHE_FILE_NAME = "cache-"
CACHE_FILE_EXT = ".jpg"

class Client:
    INIT = 0
    READY = 1
    PLAYING = 2
    state = INIT

    SETUP = 0
    PLAY = 1
    PAUSE = 2
    FORWARD = 3
    BACKWARD = 4
    DESCRIBE = 5
    SWITCH = 6
    TEARDOWN = 7

    lossCounter = 0
    # Initiation..
    def __init__(self, master, serveraddr, serverport, rtpport, filename):
        self.master = master
        self.master.protocol("WM_DELETE_WINDOW", self.handler)

        # Count Down Timer
        self.remainingTime = StringVar()
        self.remainingTime.set('00')

        # SWITCH GUI SUPPORT
        self.filenames = []
        self.fileNameVar = StringVar(master)
        self.fileNameVar.set('video.mjpeg')
        self.ChangedFileName = filename

        self.createWidgets()
        self.serverAddr = serveraddr
        self.serverPort = int(serverport)
        self.rtpPort = int(rtpport)
        self.fileName = filename
        self.rtspSeq = 0
        self.sessionId = 0
        self.requestSent = -1
        self.teardownAcked = 0
        self.connectToServer()
        self.frameNbr = 0
        self.prevFrameTime = 0
        self.lastFrameTime = 0
        self.recFrameNbr = -1
        self.endframeNbr = 0
        self.setupMovie()



    # THIS GUI IS JUST FOR REFERENCE ONLY, STUDENTS HAVE TO CREATE THEIR OWN GUI
    def createWidgets(self):
        """Build GUI."""
        # Create a label to display
        self.background = ImageTk.PhotoImage(Image.open('background.jpg'))
        self.videoFrame = Frame(self.master)
        self.statsLabel = Label(self.master, text = "Statistics Information", width = 30)
        self.statsLabel.pack(side=RIGHT)
        self.videoFrame.pack()
        self.buttonFrame = Frame(self.master)
        self.buttonFrame.pack()

         # Create Setup button
        # self.start = Button(self.buttonFrame, width=10, padx=3, pady=3)
        # self.start["text"] = "Setup"
        # self.start["command"] = self.setupMovie
        # self.start.grid(row=3, column=2, padx=2, pady=2)

        # Create Pause button
        self.start = Button(self.buttonFrame, width=10, padx=3, pady=3)
        self.start["text"] = "Pause"
        self.start["command"] = self.pauseMovie
        self.start.grid(row=3, column=2, padx=2, pady=2)

        # Create Teardown button
        self.start = Button(self.buttonFrame, width=10, padx=3, pady=3)
        self.start["text"] = "Teardown"
        self.start["command"] = self.exitClient
        self.start.grid(row=2, column=3, padx=2, pady=2)

        # Create Play button
        self.start = Button(self.buttonFrame, width=10, padx=3, pady=3)
        self.start["text"] = "Play"
        self.start["command"] = self.playMovie
        self.start.grid(row=1, column=1, padx=2, pady=2)

        # Create Fordward button
        self.forward = Button(self.buttonFrame, width=10, padx=3, pady=3)
        self.forward["text"] = "Forward"
        self.forward["command"] = self.forwardMovie
        self.forward.grid(row=1, column=2, padx=2, pady=2)

        # Create Backward button
        self.backward = Button(self.buttonFrame, width=10, padx=3, pady=3)
        self.backward["text"] = "Backward"
        self.backward["command"] = self.backwardMovie
        self.backward.grid(row=1, column=0, padx=2, pady=2)

        # Create Describe button
        self.describe = Button(self.buttonFrame, width=10, padx=3, pady=3)
        self.describe["text"] = "Describe"
        self.describe["command"] =  self.describeMovie
        self.describe.grid(row=2, column=0, padx=2, pady=2)

        # Create Switchbutton
        self.switch = Button(self.buttonFrame, width=10, padx=3, pady=3)
        self.switch["text"] = "Switch"
        self.switch["command"] = self.switchMovie
        self.switch.grid(row=3, column=0, padx=2, pady=2)

        # Create a Menu Option
        self.dropbar = OptionMenu(self.buttonFrame, self.fileNameVar, ['video.mjpeg'])
        self.dropbar.grid(row=3, column=1, padx=2, pady=2)
        self.dropbar.config(width=15, padx=3, pady=3)

        # Create a place to display remaining time
        self.timer = Entry(self.buttonFrame, width=15, justify='center', textvariable=self.remainingTime)
        self.timer.grid(row=2, column=2, padx=3, pady=3)


        self.videoLabel = Label(self.videoFrame, image=self.background)
        self.videoLabel.pack()


    def setupMovie(self):
        """Setup button handler."""
        print("Setup Movie.")
        if self.state == self.INIT:
            self.sendRtspRequest(self.SETUP) #send setup request


    def exitClient(self):
        """Teardown button handler."""
        if self.state == self.INIT:
            messagebox.showwarning('Warning', 'No video streaming to teardown')
            sys.exit(0)
        elif self.state == self.PLAYING or self.state == self.READY:
            # Close the gui window
            self.master.destroy()

            # Delete the cache image from video
            cacheFile = CACHE_FILE_NAME + str(self.sessionId) + CACHE_FILE_EXT
            if os.path.isfile(cacheFile):
                os.remove(cacheFile)

            self.sendRtspRequest(self.TEARDOWN) #send teardown request
            sys.exit(0)

    def pauseMovie(self):
        """Pause button handler."""
        print ("Pause Movie.")
        if self.state == self.PLAYING:
            self.sendRtspRequest(self.PAUSE) #send pause request

    def forwardMovie(self):
        """Forward button handler."""
        if self.state == self.PLAYING:
            self.sendRtspRequest(self.FORWARD) #send forward request

    def backwardMovie(self):
        """Backward button handler."""
        if self.state == self.PLAYING:
            self.sendRtspRequest(self.BACKWARD) #send backward request

    def playMovie(self):
        """Play button handler."""
        if self.state == self.READY:
            # Create a new thread to listen for RTP packets
            print ("Playing Movie.")
            threading.Thread(target=self.listenRtp).start()
            self.playEvent = threading.Event()
            self.playEvent.clear()
            self.sendRtspRequest(self.PLAY) #send play request

        elif self.state == self.PLAYING:
            messagebox.showwarning('Warning', 'The video streaming is playing')

    def describeMovie(self):
        """Describe button handler."""
        print ("Describe Movie.")
        if not self.state == self.INIT:
            self.sendRtspRequest(self.DESCRIBE) #send describe request
        else:
            messagebox.showwarning('Warning','Unable to retrieve information about movie.')

    def switchMovie(self):
        """Backward button handler."""
        self.fileName = self.ChangedFileName
        self.sendRtspRequest(self.SWITCH) #send switch request

    def updateCountDownTimer(self):
        remainingTime = (self.noFrames - self.frameNbr) / self.fps #formula of calcualting remainingtime
        self.remainingTime.set("Remaining: " + str(remainingTime) + 's')
        self.buttonFrame.update()

    def listenRtp(self):
        """Listen for RTP packets."""
        while True:
            try:
                data = self.rtpSocket.recv(20480)
                if data:
                    rtpPacket = RtpPacket()
                    rtpPacket.decode(data)
                    currFrameNbr = rtpPacket.seqNum()
                    try:
                        if self.frameNbr + 1 != currFrameNbr:
                            self.lossCounter += 1
                            print ( "PACKET LOSS: No." + str(currFrameNbr) )

                    except:
                        print ("seqNum() error")

                    if int(self.frameNbr) % int(self.fps) == 0 or self.frameNbr == self.noFrames:
                            self.updateCountDownTimer()

                    #EXTEND 1: Calculate the statistics
                    current = time.time()
                    duration = current - self.prevFrameTime
                    self.prevFrameTime = current
                    speed = len(rtpPacket.getPayload()) / duration
                    fps = 1 / duration
                    lossRate = float(self.lossCounter/self.frameNbr) * 100 if self.frameNbr != 0 else 0

                    # Display info to the label
                    self.displayText = StringVar()

                    statsInfo = self.displayText.get()
                    statsInfo += 'RTP current packet number: ' + str(currFrameNbr) + '\n'
                    statsInfo += 'RTP packet loss: ' + str(self.lossCounter) + ' packet(s)\n'
                    statsInfo += 'RTP packet loss rate: {:.2f} %\n'.format(lossRate)
                    statsInfo += 'Frames per second: {:.2f} FPS\n'.format(fps)
                    statsInfo += 'Frame duration: {:.0f} ms\n'.format(duration * 1000)
                    statsInfo += 'Video data rate: {:.2f}'.format(speed/1e+6) + ' Mbps\n'
                    statsInfo += '-' * 40 + '\n'
                    self.displayText.set(statsInfo)

                    self.statsLabel.configure(textvariable = self.displayText, justify=LEFT)

                    # Update the current frame to the latest frame
                    if currFrameNbr > self.frameNbr:
                        self.frameNbr = currFrameNbr
                        self.updateMovie(self.writeFrame(rtpPacket.getPayload()))

            except:
                # Stop listening upon requesting PAUSE or TEARDOWN or STOP
                if self.playEvent.isSet():
                    break

                # Upon receiving ACK for TEARDOWN request,
                # close the RTP socket
                if self.teardownAcked == 1:
                    self.rtpSocket.shutdown(socket.SHUT_RDWR)
                    self.rtpSocket.close()
                    break

    def writeFrame(self, data):
        """Write the received frame to a temp image file. Return the image file."""
        cachename = CACHE_FILE_NAME + str(self.sessionId) + CACHE_FILE_EXT
        try:
            file = open(cachename, "wb")
        except:
            print ("Cannot open file")
        try:
            file.write(data)
        except:
            print ("Cannot write to file")
        file.close()
        return cachename

    def updateMovie(self, imageFile):
        """Update the image file as video frame in the GUI."""
        try:
            photo = ImageTk.PhotoImage(Image.open(imageFile))
        except:
            print ("Cannot open photo")

        self.videoLabel.configure(image = photo, width = 600, height = 400)
        self.videoLabel.image = photo

    def connectToServer(self):
        """Connect to the Server. Start a new RTSP/TCP session."""
        self.rtspSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            self.rtspSocket.connect((self.serverAddr, self.serverPort))
            print ("Server Connection succeeded")
        except:
            messagebox.showwarning('Connection Failed', 'Connection to {} failed.'.format(self.serverAddr))

    def sendRtspRequest(self, requestCode):
        """Send RTSP request to the server."""
        #-------------
        # TO COMPLETE
        #-------------
        # Setup request
        print("\nData sent: ")
        if requestCode == self.SETUP and self.state == self.INIT:
            threading.Thread(target=self.recvRtspReply).start()
            # Update RTSP sequence number.
            self.rtspSeq += 1

            # RTSP request and send to the server.
            request = "SETUP " + str(self.fileName) + " RTSP/1.0\n" + \
                      "CSeq: " + str(self.rtspSeq) + "\n" + \
                      "Transport: RTP/UDP; client_port= " + str(self.rtpPort)

            # Assign track of the sent request.
            self.requestSent = self.SETUP

        # Play request
        elif requestCode == self.PLAY and self.state == self.READY:
            # Update RTSP sequence number.
            self.rtspSeq += 1

            # RTSP request and send to the server.
            request = "PLAY " + str(self.fileName) + " RTSP/1.0\n" + \
                      "CSeq: " + str(self.rtspSeq) + "\n" + \
                      "Session: " + str(self.sessionId)

            # Assign track of the sent request.
            self.requestSent = self.PLAY

        # Pause request
        elif requestCode == self.PAUSE and self.state == self.PLAYING:
            # Update RTSP sequence number.
            self.rtspSeq += 1

            # RTSP request and send to the server.
            request = "PAUSE " + str(self.fileName) + " RTSP/1.0\n" + \
                      "CSeq: " + str(self.rtspSeq) + "\n" + \
                      "Session: " + str(self.sessionId)

            # Assign track of the sent request.
            self.requestSent = self.PAUSE

        # Forward request
        elif requestCode == self.FORWARD:
            # Update RTSP sequence number.
            # ...
            self.rtspSeq +=  1
            # Write the RTSP request to be sent.
            # request = ...
            request = "FORWARD " + str(self.fileName) + " RTSP/1.0\n" + \
                      "CSeq: " + str(self.rtspSeq) + "\n" + \
                      "Session: " + str(self.sessionId)

            # Assign track of the sent request.
            # self.requestSent = ...
            self.requestSent = self.FORWARD
            if self.frameNbr < self.noFrames:
                if self.noFrames - self.frameNbr >= self.fps:
                    self.frameNbr += self.fps
                else:
                    self.frameNbr = self.noFrames - 1

        # Backward request
        elif requestCode == self.BACKWARD:
            # Update RTSP sequence number.
            # ...
            self.rtspSeq +=  1
            # Write the RTSP request to be sent.
            # request = ...
            request = "BACKWARD " + str(self.fileName) + " RTSP/1.0\n" + \
                      "CSeq: " + str(self.rtspSeq) + "\n" + \
                      "Session: " + str(self.sessionId)

            # Assign track of the sent request.
            # self.requestSent = ...

            self.requestSent = self.BACKWARD
            if self.frameNbr > 0:
                self.frameNbr -= self.fps

        # Teardown request
        elif requestCode == self.TEARDOWN and not self.state == self.INIT:
            # Update RTSP sequence number.
            self.rtspSeq +=  1
            # RTSP request and send to the server.
            request = "TEARDOWN " + str(self.fileName) + " RTSP/1.0\n" + \
                      "CSeq: " + str(self.rtspSeq) + "\n" + \
                      "Session: " + str(self.sessionId)


            # Assign track of the sent request.
            self.requestSent = self.TEARDOWN

        # Describe request
        elif requestCode == self.DESCRIBE and not self.state == self.INIT:
            # Update RTSP sequence number.
            self.rtspSeq +=  1

            # RTSP request and send to the server.
            request = "DESCRIBE " + str(self.fileName) + " RTSP/1.0\n" + \
                      "CSeq: " + str(self.rtspSeq) + "\n" + \
                      "Session: " + str(self.sessionId)

            # Assign track of the sent request.
            self.requestSent = self.DESCRIBE

        # Switch request
        elif requestCode == self.SWITCH:
            # Update RTSP sequence number.
            self.rtspSeq +=  1

            # RTSP request and send to the server.
            request = "SWITCH " + str(self.fileName) + " RTSP/1.0\n" + \
                      "CSeq: " + str(self.rtspSeq) + "\n" + \
                      "Session: " + str(self.sessionId)

            # Keep track of the sent request.
            self.requestSent = self.SWITCH
            self.frameNbr = 0 #return 0 to start a new video

        else:
            return

        self.rtspSocket.send(request.encode())
        print(request)

    def recvRtspReply(self):
        """Receive RTSP reply from the server."""
        while True:
            reply = self.rtspSocket.recv(1024)

            if reply:
                self.parseRtspReply(reply.decode("utf-8"))

            # Close the RTSP socket upon requesting Teardown
            if self.requestSent == self.TEARDOWN:
                self.rtspSocket.shutdown(socket.SHUT_RDWR)
                self.rtspSocket.close()
                break

    def fileNameCallBack(self, *args):
        self.ChangedFileName = str(self.fileNameVar.get())

    def parseRtspReply(self, data):
        #['RTSP/1.0 200 OK', 'CSeq: 3', 'Session: 668460', 'Total time: 20.0', 'Mean FPS: 25', 'Total frames: 500', 'Media: coolcat.mjpeg movie.Mjpeg vid.mjpeg']
        """Parse the RTSP reply from the server."""
        lines = data.split('\n')
        seqNum = int(lines[1].split(' ')[1])

        # Parse total time, FPS, total frames
        self.totalTime = float(lines[3].split(' ')[2])
        self.fps = int(lines[4].split(' ')[2])
        self.noFrames = int(lines[5].split(' ')[2])

        # Parse file names
        if len(lines[6].split(' ')) - 1 > len(self.filenames):
            for i in lines[6].split(' '):
                if i == 'Media:':
                    continue
                self.filenames.append(i)
            self.updateOptionMenu()
        # Sort out duplicates
        self.filenames = sorted(set(self.filenames))

        # Create a slot to display time
        if self.requestSent == self.SETUP or self.requestSent == self.SWITCH:
            self.total = Button(self.buttonFrame, width=10, padx=2, pady=2)
            self.total["text"] = "Total: " + str(self.totalTime) + "s"
            self.total.grid(row=2, column=1, padx=2, pady=2)

        # Process only if the server reply's sequence number is the same as the request's
        if seqNum == self.rtspSeq:
            session = int(lines[2].split(' ')[1])
            # New RTSP session ID
            if self.sessionId == 0:
                self.sessionId = session

            # Process only if the session ID is the same and the code is 200
            if self.sessionId == session and int(lines[0].split(' ')[1]) == 200:
                if self.requestSent == self.SETUP:
                    self.state = self.READY
                    self.openRtpPort()

                    # Get total time of video to remaining time
                    self.remainingTime.set("Remaining: " + str(self.totalTime)+'s')
                    self.buttonFrame.update()

                elif self.requestSent == self.PLAY:
                    self.state = self.PLAYING

                elif self.requestSent == self.DESCRIBE:
                    lines = data.split('\n')[3:]
                    info = '\n'.join(lines)
                    messagebox.showinfo('Video Information', info)

                elif self.requestSent == self.PAUSE:
                    self.state = self.READY
                    # The play thread exits. A new thread is created on resume.
                    self.playEvent.set()

                elif self.requestSent == self.TEARDOWN:
                    # Set the teardownAcked to close the socket.
                    self.teardownAcked = 1

                elif self.requestSent == self.SWITCH:
                        self.state = self.READY

                        # Get total time of video to remaining time after SWITCHING video
                        self.remainingTime.set("Remaining: " + str(self.totalTime)+'s')
                        self.buttonFrame.update()

    def openRtpPort(self):
        """Open RTP socket binded to a specified port."""
        #-------------
        # TO COMPLETE
        #-------------
        # Set the timeout value of the socket to 0.5sec
        self.rtpSocket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.rtpSocket.settimeout(0.5)

        # Create a new datagram socket to receive RTP packets from the server
        try:
            """ setup RTP/UDP socket """
            self.state = self.READY
            self.rtpSocket.bind(('',self.rtpPort))
            print ("Bind RtpPort Success")
        except:
            messagebox.showwarning('Connection Failed', 'Connection to rtpServer failed...')

# Utils Functions
    def handler(self):
        """Handler on explicitly closing the GUI window."""
        previousState = self.state
        self.pauseMovie()
        if messagebox.askokcancel("Exit?", "Do you want to exit?"):
            self.exitClient()
        else: # When the user presses cancel, resume playing.
            if previousState == self.PLAYING:
                self.playMovie()

    # Create a drop bar
    def updateOptionMenu(self):
        OPTIONS = self.filenames
        if len(self.filenames) == 0:
            OPTIONS = ['']
        self.dropbar = OptionMenu(self.buttonFrame, self.fileNameVar, *OPTIONS)
        self.dropbar.grid(row=3, column=1, padx=2, pady=2)
        self.dropbar.config(width=15, padx=3, pady=3)
        self.fileNameVar.trace("w", self.fileNameCallBack)
