Getting Started with Schola
===========================


Install Prerequisites
---------------------

.. tabs::

   .. group-tab:: Linux

      - `Ubuntu 22.04 <https://releases.ubuntu.com/jammy/>`_ (22.04.4 Desktop x86 64-bit is recommended for reproducibility)
      - `Unreal Engine 5.5 <https://www.unrealengine.com/en-US/linux>`__ (5.5.2 is recommended for reproducibility)
      - `Python 3.9 or newer <https://www.python.org/downloads/release/python-3919/>`_ 
  
      .. note::
         While other Integrated Development Environments (IDEs) can be used, `Visual Studio Code <https://code.visualstudio.com/download>`_ is recommended along with the `C/C++ Extension Pack <https://marketplace.visualstudio.com/items?itemName=ms-vscode.cpptools>`_. Please see the `Unreal Engine documentation <https://dev.epicgames.com/documentation/en-us/unreal-engine/setting-up-visual-studio-code-for-unreal-engine>`_ for more information. 
   
   .. group-tab:: Windows

      - `Windows 11 <https://www.microsoft.com/en-us/software-download/windows11>`_ or `Windows 10 <https://www.microsoft.com/en-us/software-download/windows10>`_
      - `Unreal Engine 5.5 <https://www.unrealengine.com/en-US/download>`__ (5.5.2 is recommended for reproducibility)
      - `Python 3.9 or newer <https://www.python.org/downloads/release/python-3919/>`_ 

      .. note::
         While other Integrated Development Environments (IDEs) can be used, `Visual Studio <https://visualstudio.microsoft.com/vs/>`__ is recommended. (Visual Studio Professional 2022 (64-bit) - LTSC 17.8 is recommended for reproducibility)
         
         Follow the `Visual Studio setup guide <https://dev.epicgames.com/documentation/en-us/unreal-engine/setting-up-visual-studio-development-environment-for-cplusplus-projects-in-unreal-engine?application_version=5.5>`_ from Epic Games to setup your Visual Studio environment for working with Unreal.


Install Schola
--------------

1. Add `Schola` to a project as an Unreal Engine Plugin, either by downloading the source, or via git.

   .. tabs::

      .. tab:: Download and Install 
         
         1. Create a folder named ``Schola`` in the ``Plugins`` folder of your Unreal Engine project.
         2. Download the zipped source code from the `Schola Repository <https://github.com/GPUOpen-LibrariesAndSDKs/Schola>`__
         3. Unzip the repository. Copy the contents of the ``Schola`` folder to the ``Schola`` folder you created in your project.

      .. code-tab:: bash Git Submodule 
         
         git submodule add https://github.com/GPUOpen-LibrariesAndSDKs/Schola.git  ./Plugins/Schola

      .. code-tab:: bash Standalone Git Repository
         
         git clone https://github.com/GPUOpen-LibrariesAndSDKs/Schola.git ./Plugins

   .. note::
      If you experience an error installing the repository with git due to a large file sizes, run the following command to increase the git buffer size:
      
      .. code-block:: bash
         
         git config –global http.postBuffer 524288000

2. Install the schola python package from `/Resources/python`.

   .. code-block:: bash

      pip install ./Plugins/Schola/Resources/python[all]
3. Using an editor of your choice, such as `Visual Studio <https://visualstudio.microsoft.com/vs/>`__ or `Visual Studio Code <https://code.visualstudio.com/download>`__ compile the project source. The Schola plugin will not appear in the editor, or be useable until the project has been compiled.
4. Launch your project as normal in Unreal Engine. You should see the Schola plugin in the Plugins section of the project settings.

Building 3rd-Party Dependencies for Schola (Optional)
-----------------------------------------------------

Schola comes bundled with all of its c++ dependencies already. However, if you want to use a different version of a
dependency, or unreal engine you may build them from source.


Building gRPC from source for Schola
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

1. Install Prerequisites

   .. tabs::

      .. group-tab:: Linux
         
         - `Ubuntu 22.04 <https://releases.ubuntu.com/jammy/>`_ (22.04.4 Desktop x86 64-bit is recommended for reproducibility)
         - `Unreal Engine <https://www.unrealengine.com/en-US/linux>`__ (5.4.4 is recommended for reproducibility)
         - `Python 3.9 <https://www.python.org/downloads/release/python-3919/>`_ (3.9.19 is recommended for reproducibility)
     
         .. note::
            While other Integrated Development Environments (IDEs) can be used, `Visual Studio Code <https://code.visualstudio.com/download>`__ is recommended along with the `C/C++ Extension Pack <https://marketplace.visualstudio.com/items?itemName=ms-vscode.cpptools>`_. Please see the `Unreal Engine documentation <https://dev.epicgames.com/documentation/en-us/unreal-engine/setting-up-visual-studio-code-for-unreal-engine>`_ for more information. 
      
      .. group-tab:: Windows
         
         -  `Git VCS <https://git-scm.com/download/win>`_
         -  `Unreal Engine <https://www.unrealengine.com/en-US/download>`__ (5.4.4 is recommended for reproducibility)
         -  `Visual Studio <https://visualstudio.microsoft.com/downloads/>`_ (2017 with VC++ tools v141 installed, or Visual Studio 2022 with VC++ tools)
         -  `CMake <https://cmake.org/>`_ (used to generate a Visual Studio solution from the ``CMakeLists.txt`` provided with gRPC)
         -  `Strawberry perl <http://strawberryperl.com/>`_ 
         -  `NASM <https://www.nasm.us/>`_

         .. note::
            Some install steps may require adding the above prerequisites to your PATH.

2. Build gRPC using the scripts in `/Resources/Build`, by running the following from the Plugin Root Dir

   .. tabs::

      .. code-tab:: bash Linux
            
         # Install Required Packages for Running the Build Script
         sudo apt update
         sudo apt-get -y install cmake git automake autoconf libtool-bin pkg-config build-essential

         # Change this to your Unreal Engine path
         UE_ROOT="~/UnrealEngine/UE_5.4"
         export UE_ROOT
         bash ./Resources/Build/linux_dependencies.sh
      
      .. note::
         You may need to manually update `libtool-bin` as old versions of `libtool-bin`` may cause errors during install.

      .. code-tab:: batch Windows

         # Change this to your Unreal Engine path if it is different than the default.
         set UE_ROOT="C:\Program Files\Epic Games\UE_5.4"
         ./Resources/Build/windows_dependencies.bat

Regenerated Protobuf and gRPC Code
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

1. Follow the steps in the `Building Schola from source` section to build gRPC from source, and get an up to date version of `protoc.exe`.

2. Run the following command to regenerate the protobuf and gRPC code.

   .. code-block:: bash

      python schola-build-proto --plugin-folder . --add-type-stubs

   .. note::

      The `--add-type-stubs` flag is optional and will generate `.pyi` files for the generated code. This is useful for IDEs that support type stubs for better code completion. However, not all protobuf/gRPC features are supported in the `.pyi` files. If you encounter issues when generating try running without the flag.



