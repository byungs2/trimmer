from moviepy.video.io.ffmpeg_tools import ffmpeg_extract_subclip
from moviepy.editor import VideoFileClip
import cv2
import json
import os

class VideoClip:
    def __init__(self, rtcp, rtcp_rtp, rtp, fixed_offset, origin, dest):
        self.rtcp = rtcp;
        self.rtcp_rtp = rtcp_rtp;
        self.rtp = rtp;
        self.rtp_diff_sec = 0.0;
        self.fixed_offset = fixed_offset;
        self.dynamic_offset = 0.0;
        self.offset = 0.0;
        self.start_abs_time = 0.0;
        self.fraction_time = 0.0;
        self.real_time = 0.0;
        self.origin_file_path = origin;
        self.dest = dest;
        self.duration = 0.0;
        self.fps = 0.0;
        self.dropped_sec = 0.0;
    def calculate(self):
        self.rtp_diff_sec = (self.rtcp_rtp - self.rtp)/90000.0;
        self.start_abs_time = (self.rtcp >> 32) - self.rtp_diff_sec;
        fraction_time = (self.rtcp & 0xffffffff);
        tmp_fraction_time = 0.0;
        for i in range(32):
           tmp_fraction_time += ((fraction_time >> i) & 1) * (2 ** (i-32));
        self.fraction_time = tmp_fraction_time;
        self.real_time = self.fraction_time + self.start_abs_time;
        clip = VideoFileClip(self.origin_file_path);
        self.duration = clip.duration;
        print('%0.20f' % self.duration, self.origin_file_path);
    def set_fps(self, fps):
        self.fps = fps;

class VideoSinker:
    def __init__(self, video_list):
        self.video_list = video_list
        self.max_diff = 0.0;
    def calculate_lock_step(self):
        for i in self.video_list:
            i.calculate();
            if(i.real_time > self.max_diff):
                self.max_diff = i.real_time
        for i in self.video_list:
            i.dynamic_offset = self.max_diff - i.real_time;
            i.offset = i.dynamic_offset + i.fixed_offset;
            print('%0.20f' % (i.offset - i.dropped_sec), i.dropped_sec, i.origin_file_path);

    def trimming_video_by_lock_step(self, hard_offset):
        index = 0;
        for i in self.video_list:
            if(i.offset - i.dropped_sec - i.fixed_offset) > 0 and index != 4 :
                ffmpeg_extract_subclip(i.origin_file_path, float(i.offset - i.dropped_sec), float(i.duration), targetname=i.dest);
            elif (index == 4) :
                print("Re-encode process");
                clip = VideoFileClip(i.origin_file_path);
                newclip= clip.subclip(i.offset + hard_offset/i.fps, int(i.duration));
                newclip.write_videofile(i.dest, fps=i.fps);
            else :
                ffmpeg_extract_subclip(i.origin_file_path, float(i.offset), float(i.duration), targetname=i.dest);
            index+=1;

class JsonReader:
    def __init__(self, json_file_path):
        self.file_path = json_file_path;
        self.json_data = 0;
    def open_data(self):
        with open(self.file_path, "r") as f:
            self.json_data = json.load(f);

def get_file_names(video_dirs, json_dirs, video_f_list, json_f_list):
    for i in range(len(video_dirs)):
        video_f_list.append(os.listdir(video_dirs[i]));
        json_f_list.append(os.listdir(json_dirs[i]));

def video_filter_cb(x):
    if x.endswith(".mp4"):
        return x;

def json_filter_cb(x):
    if x.endswith(".json"):
        return x;

def filtering_and_sorting(video_f_list, json_f_list):
    v_tmp = [];
    j_tmp = [];
    for i in range(len(video_f_list)):
        list_a = [];
        list_b = [];
        for j in video_f_list[i]:
            if j.endswith(".mp4") and not j.startswith("rotate_depth"):
                list_a.append(j);
        for k in json_f_list[i]:
            if k.endswith(".json") and not k.endswith("depth_rtp.json") and not k.endswith("depth_rtcp.json"):
                list_b.append(k);
        v_tmp.append(list_a);
        j_tmp.append(list_b);
        v_tmp[i].sort();
        j_tmp[i].sort();
    return v_tmp, j_tmp;

def calculate_dropped_frame(clip, threshold, fps, rtp_list) :
    before = 0.0;
    current = 0.0;
    diff = 0.0;
    dropped = 0.0;
    step = 90000.0/fps;
    odd_cnt = 0;
    init = 0.0;
    for i in rtp_list :
        if(odd_cnt%2 == 1):
            current = i;
            diff = current - before;
            if (diff > step * threshold) and init != 0.0 :
                dropped += (diff/90000.0);
            before = current;
            init = 1.0;
        odd_cnt += 1;
    clip.dropped_sec = dropped;

def video_list_maker(video_list, v, j, json_dir_list, video_dir_list):
    pre_fix = "./cutted/cutted_"

    for i in range(len(j)):
        v_list = [];
        dirs = pre_fix + str(i);
        if not os.path.exists(dirs):
            os.makedirs(dirs);
            print("Make dir complete");
        else :
            print("Exist dir");

        for k in range(len(j[i])):
            if k%2 == 0:
                rtcp_json_reader = JsonReader(json_dir_list[i] + "/" + j[i][k]);
                rtp_json_reader = JsonReader(json_dir_list[i] + "/" + j[i][k+1]);
                rtcp_json_reader.open_data();
                rtp_json_reader.open_data();
                clip = VideoClip(rtcp_json_reader.json_data["rtcp_packets"][0], 
                        rtcp_json_reader.json_data["rtcp_packets"][1], 
                        rtp_json_reader.json_data["rtp_packets"][1], 
                        10.0, 
                        video_dir_list[i] + "/" + v[i][int(k/2)], 
                        "./cutted/cutted_" + str(i) + "/" + v[i][int(k/2)]);
                v_list.append(clip);
                cv_clip = cv2.VideoCapture(clip.origin_file_path);
                fps_cv = cv_clip.get(cv2.CAP_PROP_FPS);
                clip.set_fps(fps_cv);
                calculate_dropped_frame(clip, 1.4, fps_cv, rtp_json_reader.json_data["rtp_packets"]);
        video_list.append(v_list);

       
if __name__ == "__main__": 
    # unit :: frame
    hard_offset_index = 0;
    hard_offset = [19.0, 19.0, 36.0, 67.0, 35.0, 46.0, 62.0, 30.0, 50.0, 12.0, 61.0, 31.0, 43.0, 56.0, 39.0, 75.0, 51.0];
    
    #video_dir_list = ["/data/_rotated_azure_1", "/data/_rotated_azure_2", "/data/_rotated_azure_3", "/data/_usb_normal", "/data/_reo_241"];
    #json_dir_list = ["/data/_azure_1", "/data/_azure_2", "/data/_azure_3", "/data/_usb_normal", "/data/_reo_241"];
     
    video_dir_list = [ "./origin/lanzhou_azure_3", "./origin/lanzhou_reo_241", "./origin/lanzhou_reo_242"];
    json_dir_list = [ "./origin/lanzhou_azure_3", "./origin/lanzhou_reo_241", "./origin/lanzhou_reo_242"];

    #video_dir_list = ["./origin/_azure_1", "./origin/_azure_2", "./origin/_azure_3", "./origin/_usb_normal", "./origin/_reo_241"];
    #json_dir_list = ["./origin/_azure_1", "./origin/_azure_2", "./origin/_azure_3", "./origin/_usb_normal", "./origin/_reo_241"];

    video_filename_list = [];
    json_filename_list = [];
    get_file_names(video_dir_list, json_dir_list, video_filename_list, json_filename_list);

    v, j = filtering_and_sorting(video_filename_list, json_filename_list);

    video_list = [];

    video_list_maker(video_list, v, j, json_dir_list, video_dir_list);

    for i in range(len(v[0])):
        instance_video_list = [];
        for j in range(len(video_list)):
            instance_video_list.append(video_list[j][i]);
        video_sinker = VideoSinker(instance_video_list);
        video_sinker.calculate_lock_step();
        #video_sinker.trimming_video_by_lock_step(hard_offset[hard_offset_index]);
        hard_offset_index += 1;
    """

    clip = VideoFileClip("./origin/_reo_241/0_4683_reo_241.mp4");
    cv_clip = cv2.VideoCapture("./origin/_reo_241/0_4683_reo_241.mp4");

    clip2 = VideoFileClip("./origin/_usb_normal/0_4683_usb_normal.mp4");
    cv_clip2 = cv2.VideoCapture("./origin/_usb_normal/0_4683_usb_normal.mp4");
    
    print(cv_clip.get(cv2.CAP_PROP_FPS));
    #print(clip.fps);
    #new_clip = clip.set_fps(cv_clip.get(cv2.CAP_PROP_FPS));
    #new_clip = clip.subclip(13.30023860931396484375, 20.0);
    #new_clip.write_videofile("./test.mp4", fps=cv_clip.get(cv2.CAP_PROP_FPS));

    newclip2= clip2.subclip(10.0, 20.0);
    newclip2.write_videofile("./test2.mp4", fps=cv_clip2.get(cv2.CAP_PROP_FPS), codec="mjpeg", preset="ultrafast", bitrate="75000K");
    #ffmpeg_extract_subclip("./origin/_reo_241/0_4647_reo_241.mp4", 4.3, float(20.0), targetname="./test.mp4");

    """
