from scipy.spatial import distance as dist
import numpy as np
import cv2
from imutils import face_utils
from imutils.video import VideoStream
from pathlib import Path
from fastai.vision import *
import imutils
import argparse
import time
import dlib

ap = argparse.ArgumentParser()
ap.add_argument("--save", dest="save", action = "store_true")
ap.add_argument("--no-save", dest="save", action = "store_false")
ap.set_defaults(save = False)
ap.add_argument("--savedata", dest="savedata", action = "store_true")
ap.add_argument("--no-savedata", dest="savedata", action = "store_false")
ap.set_defaults(savedata = False)
args = vars(ap.parse_args())

path = '/Users/joycezheng/FacialRecognitionVideo/'
learn = load_learner(path, 'export.pkl')

face_cascade = cv2.CascadeClassifier("haarcascade_frontalface_default.xml")

vs = VideoStream(src=0).start()
start = time.perf_counter()



data = []
time_value = 0

EYE_AR_THRESH = 0.3
EYE_AR_CONSEC_FRAMES = 10

COUNTER = 0
ALARM_ON = False

def eye_aspect_ratio(eye):
	A = dist.euclidean(eye[1], eye[5])
	B = dist.euclidean(eye[2], eye[4])
	C = dist.euclidean(eye[0], eye[3])
	ear = (A + B) / (2.0 * C)
	return ear
def text_display_results(image, prediction):
    font = cv2.FONT_HERSHEY_SIMPLEX
    fontScale = 0.7
    color = (255, 255, 255)
    thickness = 2
    text = str(prediction)+" "
    (text_width, text_height) = cv2.getTextSize(text, font, fontScale=fontScale, thickness=1)[0]
    text_offset_x = 10
    text_offset_y = image.shape[0] - 25
    cv2.putText(image, text, (text_offset_x, text_offset_y), font, fontScale, color, thickness, cv2.LINE_AA)


def data_time(time_value, prediction, probability, ear):
    current_time = int(time.perf_counter()-start)
    if current_time != time_value:
        data.append([current_time, prediction, probability, ear])
        time_value = current_time
    return time_value



detector = dlib.get_frontal_face_detector()
predictor = dlib.shape_predictor("shape_predictor_68_face_landmarks.dat")

(lStart, lEnd) = face_utils.FACIAL_LANDMARKS_IDXS["left_eye"]
(rStart, rEnd) = face_utils.FACIAL_LANDMARKS_IDXS["right_eye"]


if args["save"]:
    out = cv2.VideoWriter(path + "liveoutput.avi", cv2.VideoWriter_fourcc('M','J','P','G'), 10, (frame_width,frame_height))
while True:
    frame = vs.read()
    frame = imutils.resize(frame, width=450)
    (frame_width, frame_height, _) = frame.shape
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    face_coord = face_cascade.detectMultiScale(gray, 1.1, 5, minSize=(30, 30))

    for coords in face_coord:
        X, Y, w, h = coords
        H, W, _ = frame.shape
        X_1, X_2 = (max(0, X - int(w * 0.3)), min(X + int(1.3 * w), W))
        Y_1, Y_2 = (max(0, Y - int(0.3 * h)), min(Y + int(1.3 * h), H))
        img_cp = gray[Y_1:Y_2, X_1:X_2].copy()
        prediction, idx, probability = learn.predict(Image(pil2tensor(img_cp, np.float32).div_(225)))

        cv2.rectangle(
                img=frame,
                pt1=(X_1, Y_1),
                pt2=(X_2, Y_2),
                color=(128, 128, 0),
                thickness=2,
            )
        rect = dlib.rectangle(X, Y, X+w, Y+h)

        text_display_results(frame, prediction)

        shape = predictor(gray, rect)
        shape = face_utils.shape_to_np(shape)
        leftEye = shape[lStart:lEnd]
        rightEye = shape[rStart:rEnd]
        leftEAR = eye_aspect_ratio(leftEye)
        rightEAR = eye_aspect_ratio(rightEye)
        ear = (leftEAR + rightEAR) / 2.0
        leftEyeHull = cv2.convexHull(leftEye)
        rightEyeHull = cv2.convexHull(rightEye)
        cv2.drawContours(frame, [leftEyeHull], -1, (0, 255, 0), 1)
        cv2.drawContours(frame, [rightEyeHull], -1, (0, 255, 0), 1)
        if ear < EYE_AR_THRESH:
            COUNTER += 1
            if COUNTER >= EYE_AR_CONSEC_FRAMES:
                cv2.putText(frame, "Distracted Driving", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
        else:
            COUNTER = 0
            ALARM_ON = False
        cv2.putText(frame, "Eye Ratio: {:.2f}".format(ear), (250, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
        time_value = data_time(time_value, prediction, probability, ear)

    cv2.imshow("frame", frame)

    if args["save"]:
            out.write(frame)
    if cv2.waitKey(1) & 0xFF == ord("q"):
        break

df = pd.DataFrame(data, columns = ['Time (seconds)', 'Expression', 'Probability', 'EAR'])
df.to_csv(path+'/exportlive.csv')

vs.stop()
if args["save"]:
    out.release()
cv2.destroyAllWindows()
