# EXPLICANDO ESSE CÓDIGO DO ZERO:
# PRIMEIRAMENTE, O OBJETIVO DESSE CÓDIGO É CRIAR UM PACOTE ROS2 PARA O ASV.
#
from setuptools import find_packages, setup # find_packages é uma função que encontra os pacotes do projeto, setup é uma função que configura o pacote.

package_name = 'asv_control' # Define o nome do pacote

setup( # Função que configura o pacote
    name=package_name, # Nome do pacote
    version='0.0.0', # Versão do pacote
    packages=find_packages(exclude=['test']), # Pacotes do projeto
    data_files=[
        ('share/ament_index/resource_index/packages', # Arquivos de dados do pacote
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']), # Arquivos de dados do pacote
    ],
    install_requires=['setuptools'], # Requisitos de instalação
    zip_safe=True, # Zip seguro
    maintainer='Michel Kleyton', # Mantenedor do pacote
    maintainer_email='[EMAIL_ADDRESS]', # Email do mantenedor
    description='Pacote de controle e teleoperacao do ASV', # Descrição do pacote
    license='Apache-2.0', # Licença do pacote
    tests_require=['pytest'], # Requisitos de teste
    entry_points={ # Pontos de entrada
        'console_scripts': [ # Scripts de console
            'teleop_node = asv_control.teleop_node:main'
        ],
    },
)