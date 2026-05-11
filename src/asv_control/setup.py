# ============================================================
# setup.py — Arquivo de configuração do pacote Python para ROS2
# ============================================================
# No ROS2, existem dois tipos de pacote:
#   1. ament_cmake  → para código C++ (usa CMakeLists.txt)
#   2. ament_python → para código Python (usa este setup.py)
#
# Este arquivo é o equivalente Python do CMakeLists.txt.
# Ele diz ao colcon (build system do ROS2):
#   - Qual é o nome do pacote
#   - Onde estão os módulos Python
#   - Quais scripts podem ser executados como comandos
# ============================================================

# Importa as ferramentas de empacotamento do Python
# find_packages → Busca automaticamente todas as pastas que são módulos Python
#                  (pastas que contêm __init__.py)
# setup → Função principal que registra todas as informações do pacote
from setuptools import find_packages, setup

# Define o nome do pacote em uma variável para reutilizar abaixo
# IMPORTANTE: Este nome DEVE ser idêntico ao <name> no package.xml
package_name = 'asv_control'

# ============================================================
# Função setup() — O "formulário de cadastro" do pacote
# ============================================================
setup(
    # Nome do pacote (deve ser igual à variável acima e ao package.xml)
    name=package_name,

    # Versão do pacote no formato X.Y.Z (semântico)
    # 0.0.0 = versão inicial de desenvolvimento
    version='0.0.0',

    # Busca automática de todos os módulos Python do projeto
    # exclude=['test'] → Ignora a pasta de testes para não instalar junto
    # Ele vai encontrar a pasta asv_control/ porque ela tem __init__.py
    packages=find_packages(exclude=['test']),

    # data_files → Arquivos que NÃO são código Python, mas precisam ser instalados
    # O ROS2 precisa deles para reconhecer e indexar o pacote
    data_files=[
        # Registra o pacote no índice do ament (sistema de pacotes do ROS2)
        # Sem isso, comandos como 'ros2 pkg list' não encontram o pacote
        # O arquivo 'resource/asv_control' é um marcador vazio obrigatório
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),

        # Copia o package.xml para a pasta share/ do pacote instalado
        # O colcon e o rosdep precisam dele para resolver dependências0.
         
        ('share/' + package_name, ['package.xml']),
    ],

    # Dependências Python necessárias para instalar este pacote
    # setuptools é o mínimo obrigatório para qualquer pacote Python
    install_requires=['setuptools'],

    # Permite que o pacote seja distribuído como um arquivo .zip
    # True = seguro para comprimir (não depende de caminhos absolutos)
    zip_safe=True,

    # Informações do mantenedor (quem cuida deste pacote)
    maintainer='Michel Kleyton',
    maintainer_email='[EMAIL_ADDRESS]',

    # Descrição curta do que o pacote faz
    description='Pacote de controle e teleoperacao do ASV',

    # Licença de uso do código
    license='Apache-2.0',

    # Framework de testes usado (pytest é o padrão do ROS2)
    tests_require=['pytest'],

    # ============================================================
    # entry_points — OS COMANDOS EXECUTÁVEIS DO PACOTE
    # ============================================================
    # Esta é a parte MAIS IMPORTANTE do setup.py
    # Aqui você registra quais scripts Python podem ser executados
    # como comandos do ROS2 (ros2 run)
    entry_points={
        'console_scripts': [
            # Formato: 'nome_do_comando = modulo.arquivo:funcao'
            #
            # Traduzindo esta linha:
            #   'teleop_node'          → nome que você digita no terminal
            #   'asv_control'          → pasta do módulo (com __init__.py)
            #   'teleop_node'          → arquivo teleop_node.py
            #   'main'                 → função main() dentro do arquivo
            #
            # Uso: ros2 run asv_control teleop_node
            'teleop_node = asv_control.teleop_node:main'
        ],
    },
)