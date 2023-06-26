import cv2
import numpy as np

# Load the image
image = cv2.imread('image.jpg')

# Convert the image to HSV color space
hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)

# Define range for blue color
lower_blue = np.array([110,50,50])
upper_blue = np.array([130,255,255])

# Create a mask
mask = cv2.inRange(hsv, lower_blue, upper_blue)

# Use Hough Line Transform to detect lines
lines = cv2.HoughLines(mask, 1, np.pi/180, 100)

# Draw the lines on the original image
if lines is not None:
    for rho, theta in lines[:, 0]:
        a = np.cos(theta)
        b = np.sin(theta)
        x0 = a * rho
        y0 = b * rho
        x1 = int(x0 + 1000 * (-b))
        y1 = int(y0 + 1000 * (a))
        x2 = int(x0 - 1000 * (-b))
        y2 = int(y0 - 1000 * (a))

        cv2.line(image, (x1, y1), (x2, y2), (0, 0, 255), 2)

# Show the image
cv2.imshow('image', image)
cv2.waitKey(0)
cv2.destroyAllWindows()
