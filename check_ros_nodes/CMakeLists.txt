
cmake_minimum_required(VERSION 2.8.3)
project(check_ros_nodes)

find_package(catkin REQUIRED COMPONENTS
  roscpp
)

catkin_package()

include_directories(
  ${catkin_INCLUDE_DIRS}
)

add_executable(check_ros_nodes src/check_ros_nodes.cpp)
target_link_libraries(check_ros_nodes ${catkin_LIBRARIES})
