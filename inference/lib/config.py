# YOLOv8 Parameter
#OBJ_THRESH = 0.25
OBJ_THRESH = 0.9
NMS_THRESH = 0.45
IMG_SIZE = 640

# YOLOv8 Classes          
CLASSES = ("correcto", "ausente","incorrecto")


# decice tree for rk356x/rk3588
DEVICE_COMPATIBLE_NODE = '/proc/device-tree/compatible'

RK356X_RKNN_MODEL = 'models/yolov5s.rknn'
RK3588_RKNN_MODEL = '/home/orangepi/Desktop/YOLOv8 to RKNN/inference/lib/models/yolov8s-640-640_rk3588.rknn'

#Webcam dev /device/video0, /device/video1 etc.
CAM_DEV = 0
CAM_DEV2 = 2

#Capture Resolution
CAM_WIDTH = 640
CAM_HEIGHT = 480

#Position Display
D1_WIDTH = 0
D1_HEIGHT = 200

D2_WIDTH = 0
D2_HEIGHT = 640
