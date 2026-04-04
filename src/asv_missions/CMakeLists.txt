cmake_minimum_required(VERSION 3.8)
project(asv_missions)

if(CMAKE_COMPILER_IS_GNUCXX OR CMAKE_CXX_COMPILER_ID MATCHES "Clang")
  add_compile_options(-Wall -Wextra -Wpedantic)
endif()

find_package(ament_cmake REQUIRED)

# Instala as pastas de missoes (plans) e scripts
install(DIRECTORY
  plans
  scripts
  DESTINATION share/${PROJECT_NAME}
)

ament_package()