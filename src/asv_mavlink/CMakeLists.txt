cmake_minimum_required(VERSION 3.8)
project(asv_mavlink)

if(CMAKE_COMPILER_IS_GNUCXX OR CMAKE_CXX_COMPILER_ID MATCHES "Clang")
  add_compile_options(-Wall -Wextra -Wpedantic)
endif()

find_package(ament_cmake REQUIRED)

# Instala a pasta launch para o comando 'ros2 launch' funcionar
install(DIRECTORY
  launch
  DESTINATION share/${PROJECT_NAME}
)

# Instala o script Python para que o comando 'ros2 run' consiga acha-lo
install(PROGRAMS
  scripts/mavlink_bridge_node.py
  DESTINATION lib/${PROJECT_NAME}
)

ament_package()