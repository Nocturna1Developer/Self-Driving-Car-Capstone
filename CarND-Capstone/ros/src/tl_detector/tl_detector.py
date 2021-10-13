#!/usr/bin/env python

#Credit

#1] Waypoint Updater (Partial) Video
#2] Waypoint Updater (Full) Video
#3] DBW Node Walkthrough Video
#4] Detection Walkthrough Video

#Used as reference: https://github.com/felipemartinezs/CarND-Capstone/tree/master/ros/src

import rospy
from std_msgs.msg import Int32
from geometry_msgs.msg import PoseStamped, Pose
from styx_msgs.msg import TrafficLightArray, TrafficLight
from styx_msgs.msg import Lane
from sensor_msgs.msg import Image
from cv_bridge import CvBridge
from light_classification.tl_classifier import TLClassifier
import tf
import cv2
import yaml
from scipy.spatial import KDTree

STATE_COUNT_THRESHOLD = 3

class TLDetector(object):
    def __init__(self):
        rospy.init_node('tl_detector') 

        self.pose = None               
        self.waypoints = None           
        self.waypoints_2d = None
        self.waypoint_tree = None
        self.camera_image = None        
        self.lights = []

        sub1 = rospy.Subscriber('/current_pose', PoseStamped, self.pose_cb)
        sub2 = rospy.Subscriber('/base_waypoints', Lane, self.waypoints_cb)
        sub3 = rospy.Subscriber('/vehicle/traffic_lights', TrafficLightArray, self.traffic_cb)
        sub6 = rospy.Subscriber('/image_color', Image, self.image_cb)

        config_string = rospy.get_param("/traffic_light_config")
        self.config = yaml.load(config_string)

        self.upcoming_red_light_pub = rospy.Publisher('/traffic_waypoint', Int32, queue_size=1)

        self.bridge = CvBridge()
        self.light_classifier = TLClassifier()
        self.listener = tf.TransformListener()

        self.state = TrafficLight.UNKNOWN
        self.last_state = TrafficLight.UNKNOWN
        self.last_wp = -1
        self.state_count = 0

        rospy.spin()

    def pose_cb(self, msg):
        self.pose = msg

    def waypoints_cb(self, waypoints):
        self.waypoints = waypoints
        if not self.waypoints_2d:
            self.waypoints_2d = [[w.pose.pose.position.x, w.pose.pose.position.y] for w in waypoints.waypoints]
            self.waypoint_tree = KDTree(self.waypoints_2d)

    def traffic_cb(self, msg):
        self.lights = msg.lights   

    def image_cb(self, msg):
        self.has_image = True
        self.camera_image = msg
        light_wp, state = self.process_traffic_lights()

        if self.state != state:    
            self.state_count = 0   
            self.state = state      
        elif self.state_count >= STATE_COUNT_THRESHOLD:   
            self.last_state = self.state 
            light_wp = light_wp if state == TrafficLight.RED else -1 
            self.last_wp = light_wp                                 
            self.upcoming_red_light_pub.publish(Int32(light_wp)) 
        else:
            self.upcoming_red_light_pub.publish(Int32(self.last_wp))    
        self.state_count += 1       

    def get_closest_waypoint(self, x, y):
        #TODO Implement
        closest_idx = self.waypoint_tree.query([x, y], 1)[1]
        return closest_idx
        '''
        You will want to use the get_closest_waypoint method to find the closest waypoints to the vehicle and lights. 
        Using these waypoint indices, you can determine which light is
        ahead of the vehicle along the list of waypoints.
        '''
        if (self.pose and self.waypoints != None):
            car_position = self.get_closest_waypoint(self.pose.pose)
        # According to the video Detection walkthorugh this code was reusable
        for i, light in enumerate(self.lights):
            line = stop_line_positions[i]
            light_pose = Pose()
            temp_wp_index = self.get_closest_waypoint(line[0], line[1])
            d = temp_wp_index - car_position
            # We dont want to go past the 8 car states (intersections), checks which is the closest traffic light
            if d >= 0 and d < diff:
                diff = d
                cloest_light = light
                line_wp_index = temp_wp_index
                if cloest_light != None:                      
                    state = self.get_light_state(cloest_light)
                    return line_wp_index, state
                
                self.waypoints = None
                return -1, TrafficLight.UNKNOWN 

    def get_light_state(self, light):
        return light.state

    def process_traffic_lights(self):
        closest_light = None
        line_wp_idx = None
        light = None

        stop_line_positions = self.config['stop_line_positions']
        if(self.pose):
            car_wp_idx = self.get_closest_waypoint(self.pose.pose.position.x, self.pose.pose.position.y)

            #TODO find the closest visible traffic light (if one exists)
            diff = len(self.waypoints.waypoints)
            for i, light in enumerate(self.lights):
                line = stop_line_positions[i]
                temp_wp_idx = self.get_closest_waypoint(line[0], line[1])
                d = temp_wp_idx - car_wp_idx
                if d >= 0 and d < diff:
                    diff = d
                    closest_light = light
                    line_wp_idx = temp_wp_idx

        if closest_light:
            state = self.get_light_state(closest_light)
            return line_wp_idx, state
            
        return -1, TrafficLight.UNKNOWN

if __name__ == '__main__':
    try:
        TLDetector()
    except rospy.ROSInterruptException:
        rospy.logerr('Could not start traffic node.')