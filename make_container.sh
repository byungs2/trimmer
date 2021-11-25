#!/bin/bash

sudo docker run -it --name trimm -v /data:/data -v /home/byunghun/workspace/video_trimming_by_rtcp:/home/workspace trimm:1.0 /bin/bash
