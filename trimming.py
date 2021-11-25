from moviepy.video.io.ffmpeg_tools import ffmpeg_extract_subclip
from moviepy.editor import VideoFileClip
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
            print('%0.20f' % i.offset, i.origin_file_path);

    def trimming_video_by_lock_step(self):
        for i in self.video_list:
            ffmpeg_extract_subclip(i.origin_file_path, i.offset, i.duration, targetname=i.dest);

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

def video_list_maker(video_list, v, j):
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
                        12.0, 
                        video_dir_list[i] + "/" + v[i][k/2], 
                        "./cutted/cutted_" + str(i) + "/" + v[i][k/2]);
                v_list.append(clip);
        video_list.append(v_list);

       
if __name__ == "__main__": 
    video_dir_list = ["/data/_rotated_azure_1", "/data/_rotated_azure_2", "/data/_rotated_azure_3", "/data/_usb_normal", "/data/_reo_241"];
    json_dir_list = ["/data/_azure_1", "/data/_azure_2", "/data/_azure_3", "/data/_usb_normal", "/data/_reo_241"];
    video_filename_list = [];
    json_filename_list = [];
    get_file_names(video_dir_list, json_dir_list, video_filename_list, json_filename_list);

    v, j = filtering_and_sorting(video_filename_list, json_filename_list);

    video_list = [];

    video_list_maker(video_list, v, j);

    for i in range(len(v[0])):
        video_list[0][i].calculate();
        video_list[1][i].calculate();
        video_list[2][i].calculate();
        video_list[3][i].calculate();
        video_list[4][i].calculate();
        video_sinker = VideoSinker([video_list[0][i], video_list[1][i], video_list[2][i], video_list[3][i], video_list[4][i]]);
        video_sinker.calculate_lock_step();
        video_sinker.trimming_video_by_lock_step();
