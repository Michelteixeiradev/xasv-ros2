cmake_minimum_required(VERSION 3.8)
project(asv_gazebo)

if(CMAKE_COMPILER_IS_GNUCXX OR CMAKE_CXX_COMPILER_ID MATCHES "Clang")
  add_compile_options(-Wall -Wextra -Wpedantic)
endif()

find_package(ament_cmake REQUIRED)

# Instala a pasta de mundos para que o Gazebo consiga acha-los
install(DIRECTORY
  worlds
  DESTINATION share/${PROJECT_NAME}
)

ament_package()