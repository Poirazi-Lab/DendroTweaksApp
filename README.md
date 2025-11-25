# DendroTweaks

<img src="https://dendrotweaks.readthedocs.io/en/latest/_static/logo.png" width="25%">
<p>

**DendroTweaks** is a Python toolbox designed for creating and validating single-cell biophysical models with active dendrites. 

It is available both as a standalone Python package and as a web-based application. This repository contains the code for the web-based application.

## Table of Contents
- [Learn More](#learn-more)
- [Publication](#publication)
- [Repository Structure](#repository-structure)
- [Installation](#installation)


## Learn More

- **Standalone Library**: Explore the [official documentation](https://dendrotweaks.readthedocs.io/en/latest/index.html) for detailed tutorials and API reference.
- **Web Application**: Access the GUI online via our platform at [dendrotweaks.dendrites.gr](https://dendrotweaks.dendrites.gr).
- **Quick Overview**: Check out our [e-poster](https://doi.org/10.57736/abba-7149), including a video demonstration, presented at the FENS Forum 2024 in Vienna.

## Publication

For an in-depth understanding of DendroTweaks, refer to our publication in *eLife*:

> Roman Makarov, Spyridon Chavlis, Panayiota Poirazi (2024).  
> *DendroTweaks: An interactive approach for unraveling dendritic dynamics.*  
> eLife 13:RP103324. [https://doi.org/10.7554/eLife.103324.1](https://doi.org/10.7554/eLife.103324.1)

If you find DendroTweaks helpful for your research, please consider citing our work:

```bibtex
@article{Makarov2024,
    title={DendroTweaks: An interactive approach for unraveling dendritic dynamics},
    author={Makarov, Roman and Chavlis, Spyridon and Poirazi, Panayiota},
    journal={eLife},
    volume={13},
    pages={RP103324},
    year={2024},
    doi={10.7554/eLife.103324.1}
}
```

## Repository Structure
This repository is organized as follows:

```plaintext
dendrotweaksapp/
│
├── app/
│   ├── presenter/                # Coordination of app components
│   │   ├── presenter.py          # Main presenter class
│   │   └── ...                   # Mixins for the presenter class
│   │
│   ├── static/                   # Static files (e.g., CSS, JS, user data)
│   ├── templates/                # HTML templates for the app
│   ├── view/                
│   │   ├── view.py               # Main view class
│   │   └── ...                   # Code to initialize GUI elements
│   │
│   ├── main.py                   # Main script to launch the Bokeh app
│   ├── bokeh_utils.py            
│   ├── default_config.json       # App configuration
│   ├── user_config.json          # User preferences
│   ├── bokeh_utils.py            
│   ├── utils.py                  
│   └── logger.py
│
├── environment.yml               # Conda environment configuration
├── requirements.txt              # Python dependencies for pip
├── README.md                     # Documentation and setup instructions
└── LICENSE                       # Project license
```

## Installation

In this section, we will explain how to locally install DendroTweaks and run it in GUI mode via a Bokeh server.

### Set Up a Conda Environment (recommended)
Create and activate a conda environment using the provided environment.yml file:

```bash
conda env create -f environment.yml
conda activate dendrotweaksapp
```

### Install Dependencies Using PIP (optional)

Alternatively, install required packages using pip:

```bash
pip install -r requirements.txt
```

### Install more graph layouts (optional)

```bash
sudo apt-get install graphviz graphviz-dev
```


### Run the Bokeh Server
To run the Bokeh server and launch the app locally, use the following command:

```bash
bokeh serve --show app
```

This will start the Bokeh server and automatically open your default web browser to display the app.


## License

This project uses multiple licenses depending on the content:

- **App code**: Mozilla Public License 2.0 (MPL-2.0).  
  All modifications to these files must remain under MPL-2.0 when redistributed.

- **Examples (`app/static/data/*`)**: no formal license; provided for demonstration purposes.  
  Use freely in your own projects.

> **Note:** Previous versions of this project were released under GPL-3.0.