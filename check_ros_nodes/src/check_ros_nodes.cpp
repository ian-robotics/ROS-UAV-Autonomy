#include <ros/ros.h>
#include <ros/master.h>
#include <vector>
#include <string>
#include <iostream>
#include <unistd.h>
#include <algorithm>
#include <mavros_msgs/StatusText.h>

using namespace std;

extern "C"
{
    void get_active_ros_nodes(vector<string> &active_nodes)
    {
        active_nodes.clear();
        ros::master::getNodes(active_nodes);
    }
}

int main(int argc, char **argv)
{
    ros::init(argc, argv, "check_ros_nodes");
    ros::NodeHandle nh;

    ros::Publisher status_pub = nh.advertise<mavros_msgs::StatusText>("/mavros/statustext/send", 50);
    sleep(1);

    vector<string> last_nodes;

    // ====================== Report all online nodes at startup ======================
    vector<string> initial_nodes;
    get_active_ros_nodes(initial_nodes);

    cout << "\n===== ROS nodes detected at startup =====" << endl;
    for (const string &node : initial_nodes)
    {
        mavros_msgs::StatusText msg;
        msg.text = "✅ Node online: " + node;
        status_pub.publish(msg);
        
        cout << msg.text << endl;
        ros::Duration(0.1).sleep();
    }
    cout << "===== Initial node announcements complete =====" << endl;

    last_nodes = initial_nodes;

    // ====================== Monitor node availability ======================
    while (ros::ok())
    {
        vector<string> current_nodes;
        get_active_ros_nodes(current_nodes);

        // Newly online nodes
        for (const string &node : current_nodes)
        {
            if (find(last_nodes.begin(), last_nodes.end(), node) == last_nodes.end())
            {
                mavros_msgs::StatusText msg;
                msg.text = "✅ Node came online: " + node;
                status_pub.publish(msg);
                cout << msg.text << endl;
            }
        }

        // Nodes no longer online
        for (const string &node : last_nodes)
        {
            if (find(current_nodes.begin(), current_nodes.end(), node) == current_nodes.end())
            {
                mavros_msgs::StatusText msg;
                msg.text = "❌ Node went offline: " + node;
                status_pub.publish(msg);
                cout << msg.text << endl;
            }
        }

        last_nodes = current_nodes;
        sleep(2);
    }

    return 0;
}
