import os
import cv2
class VideoStream:
    def __init__(self, filename):
        self.filename = filename
        self.wholeVideo = []
        try:
            self.file = open(filename, 'rb')
        except:
            raise IOError
        self.frameNum = 0
        
    def nextFrame(self, forward, backward):
        """Get next frame."""
        # Backward frame processing
        moveFrames = 0
        
        if backward == 1:
            for x in range(self.fps):  # default move 1 second
                if self.frameNum != 0:
                    moveFrames += (5 + self.wholeVideo[self.frameNum-1])
                    self.frameNum -= 1
            self.file.seek(-moveFrames, os.SEEK_CUR)

        # Forward frame processsing
        if forward == 1:
            noMoveFrames = 0
            for x in range(self.fps):  # default move 1 second
                if self.frameNum < len(self.wholeVideo):
                    moveFrames += (5 + self.wholeVideo[self.frameNum])
                    self.frameNum += 1
                    noMoveFrames += 1
            self.file.seek(moveFrames, os.SEEK_CUR)

            # Forward to the last frame if the number of frames need to move less than FPS
            if noMoveFrames < self.fps:
                lastFrame = self.wholeVideo[len(self.wholeVideo)-1]
                self.file.seek(-5 - lastFrame, os.SEEK_CUR)
                data = self.file.read(5)
                data = self.file.read(lastFrame)
                return data
        
        # Get the framelength from the first 5 bits
        data = self.file.read(5)
        
        if data:
            framelength = int(data)

            # Read the current frame
            data = self.file.read(framelength)
            self.frameNum += 1
        return data

    def getWholeVideo(self):
        """Append to the list"""
        if self.filename:
            # Get the framelength from the first 5 bits
            data = self.file.read(5)
            if data:
                framelength = int(data)
                self.wholeVideo.append(framelength)
                data = self.file.read(framelength)
            return data

    def calNumFrames(self):
        """Get total number of frames."""
        while self.getWholeVideo():
            pass
        self.numFrames = len(self.wholeVideo)
        self.file.close()
        self.file = open(self.filename, 'rb')

    def calFps(self):
        """Get frames per second."""
        cap = cv2.VideoCapture("./{0}".format(self.filename))
        self.fps = int(cap.get(cv2.CAP_PROP_FPS))

    def calTotalTime(self):
        """Get total time of the video."""
        self.calNumFrames()
        self.calFps()
        self.totalTime = self.numFrames / self.fps

    def getSize(self):
        file_stats = os.stat(self.filename)
        return file_stats.st_size
        
    def frameNbr(self):
        """Get frame number."""
        return self.frameNum

    def resetFrame(self):
        """Reset the movie frame"""
        self.file.seek(0)
        self.frameNum = 0
    

    
