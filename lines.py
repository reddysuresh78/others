
import cv2
import numpy as np

img = cv2.imread('/Users/sureshreddy/input.png')
gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
edges = cv2.Canny(gray, 50, 150, apertureSize=3)
lines_list =[]
lines = cv2.HoughLinesP(
            edges, # Input edge image
            1, # Distance resolution in pixels
            np.pi/180, # Angle resolution in radians
            threshold=20, # Min number of votes for valid line
            minLineLength=50, # Min allowed length of line
            maxLineGap=50 # Max allowed gap between line for joining them
            )

print(len(lines))
  
# Iterate over points
for points in lines:
      # Extracted points nested in the list
    x1,y1,x2,y2=points[0]
    # Draw the lines joing the points
    # On the original image
    cv2.line(img,(x1,y1),(x2,y2),(0,255,0),2)
    # Maintain a simples lookup list for points
    lines_list.append([(x1,y1),(x2,y2)])

cv2.imshow('image', img)
cv2.waitKey(0)
cv2.destroyAllWindows()
