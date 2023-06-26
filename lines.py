import cv2
import numpy as np
import matplotlib.pyplot as plt

# image path:
#path = "D://opencvImages//"
#fileName = "out.jpg"

# Reading an image in default mode:
inputImage = cv2.imread('image.jpg')

# Convert RGB to grayscale:
grayscaleImage = cv2.cvtColor(inputImage, cv2.COLOR_BGR2GRAY)

# Convert the BGR image to HSV:
hsvImage = cv2.cvtColor(inputImage, cv2.COLOR_BGR2HSV)

# Create the HSV range for the blue ink:
# [128, 255, 255], [90, 50, 70]
lowerValues = np.array([90, 50, 70])
upperValues = np.array([128, 255, 255])

# Get binary mask of the blue ink:
bluepenMask = cv2.inRange(hsvImage, lowerValues, upperValues)
# Use a little bit of morphology to clean the mask:
# Set kernel (structuring element) size:
kernelSize = 3
# Set morph operation iterations:
opIterations = 1
# Get the structuring element:
morphKernel = cv2.getStructuringElement(cv2.MORPH_RECT, (kernelSize, kernelSize))
# Perform closing:
bluepenMask = cv2.morphologyEx(bluepenMask, cv2.MORPH_CLOSE, morphKernel, None, None, opIterations, cv2.BORDER_REFLECT101)

# Add the white mask to the grayscale image:
colorMask = cv2.add(grayscaleImage, bluepenMask)
_, binaryImage = cv2.threshold(colorMask, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
cv2.imwrite('bwimage.jpg',binaryImage)
thresh, im_bw = cv2.threshold(binaryImage, 210, 230, cv2.THRESH_BINARY)
kernel = np.ones((1, 1), np.uint8)
imgfinal = cv2.dilate(im_bw, kernel=kernel, iterations=1)
cv2.imshow("final",imgfinal)
cv2.waitKey(0)
cv2.destroyAllWindows()
