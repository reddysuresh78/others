"""
Detect the best 4 lines for a rounded rectangle.
"""

import numpy as np
import cv2

input_image = cv2.imread("image.jpg")

def drawLines(img, lines):
    """
    Draw lines on an image
    """
    for line in lines:
        for rho,theta in line:
            a = np.cos(theta)
            b = np.sin(theta)
            x0 = a*rho
            y0 = b*rho
            x1 = int(x0 + 1000*(-b))
            y1 = int(y0 + 1000*(a))
            x2 = int(x0 - 1000*(-b))
            y2 = int(y0 - 1000*(a))
            cv2.line(img, (x1,y1), (x2,y2), (0,0,255), 1)

input_image_grey = cv2.cvtColor(input_image, cv2.COLOR_BGR2GRAY)
edged = input_image_grey

rho = 1 # 1 pixel
theta = 1.0*0.017 # 1 degree
threshold = 100
lines = cv2.HoughLines(edged, rho, theta, threshold)

# Fix negative angles
num_lines = lines.shape[1]
for i in range(0, num_lines):
    line = lines[0,i,:]
    rho = line[0]
    theta = line[1]
    if rho < 0:
        rho *= -1.0
        theta -= np.pi
        line[0] = rho
        line[1] = theta

# Draw all Hough lines in red
img_with_all_lines = np.copy(input_image)
drawLines(img_with_all_lines, lines)
cv2.imshow("Hough lines", img_with_all_lines)
cv2.waitKey()
cv2.imwrite("all_lines.jpg", img_with_all_lines)

# Find 4 lines with unique rho & theta:
num_lines_to_find = 4
filtered_lines = np.zeros([1, num_lines_to_find, 2])

if lines.shape[1] < num_lines_to_find:
    print("ERROR: Not enough lines detected!")

# Save the first line
filtered_lines[0,0,:] = lines[0,0,:]
print("Line 1: rho = %.1f theta = %.3f" % (filtered_lines[0,0,0], filtered_lines[0,0,1]))
idx = 1 # Index to store the next unique line
# Initialize all rows the same
for i in range(1,num_lines_to_find):
    filtered_lines[0,i,:] = filtered_lines[0,0,:]

# Filter the lines
num_lines = lines.shape[1]
for i in range(0, num_lines):
    line = lines[0,i,:]
    rho = line[0]
    theta = line[1]

    # For this line, check which of the existing 4 it is similar to.
    closeness_rho   = np.isclose(rho,   filtered_lines[0,:,0], atol = 10.0) # 10 pixels
    closeness_theta = np.isclose(theta, filtered_lines[0,:,1], atol = np.pi/36.0) # 10 degrees

    similar_rho = np.any(closeness_rho)
    similar_theta = np.any(closeness_theta)
    similar = (similar_rho and similar_theta)

    if not similar:
        print("Found a unique line: %d rho = %.1f theta = %.3f" % (i, rho, theta))
        filtered_lines[0,idx,:] = lines[0,i,:]
        idx += 1
   
    if idx >= num_lines_to_find:
        print("Found %d unique lines!" % (num_lines_to_find))
        break

# Draw filtered lines
img_with_filtered_lines = np.copy(input_image)
drawLines(img_with_filtered_lines, filtered_lines)
cv2.imshow("Filtered lines", img_with_filtered_lines)
cv2.waitKey()
cv2.imwrite("filtered_lines.jpg", img_with_filtered_lines)
