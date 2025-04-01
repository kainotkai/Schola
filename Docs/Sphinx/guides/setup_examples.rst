Getting Started With Schola Examples
====================================

This guide will walk you through setting up the Schola Experiments Project to try out some premade reinforcement learning examples with Schola.


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


Install Schola Examples
-----------------------

1. Get the `ScholaExamples` project, either by downloading the source, or via git.

    .. tabs::

        .. tab:: Manual Download 
         
            1. Download the zipped source code from the `Schola Examples Repository <https://github.com/GPUOpen-LibrariesAndSDKs/ScholaExamples>`__
            2. Unzip the project.

        .. tab:: Clone Repository

            .. code-block:: bash

                git clone --recurse-submodules https://github.com/GPUOpen-LibrariesAndSDKs/ScholaExamples.git

            .. note::
                If you experience an error installing the repository with git due to a large file sizes, run the following command to increase the git buffer size:
                
                .. code-block:: bash
                    
                    git config -–global http.postBuffer 524288000

2. Install the schola python package from `./Plugins/Schola/Resources/python`.

    .. code-block:: bash

        pip install ./Plugins/Schola/Resources/python[all]

3. Launch the Project.
   
.. seealso::

    For setting up your project files to run ScholaExample, please refer to the guide on `Project Files for IDEs <https://dev.epicgames.com/documentation/en-us/unreal-engine/how-to-generate-unreal-engine-project-files-for-your-ide>`_ from Epic Games.