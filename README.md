# DendroTweaks

<img src="app/static/images/logo.png" width="25%">
<p>

A toolbox for exploring dendritic dynamics.

## Table of Contents

- [Repository Structure](#repository-structure)
- [Installation](#installation)
- [Usage](#usage)
- [Troubleshooting](#troubleshooting)


## Repository Structure
The repository is organized as follows:

```plaintext
dendrotweaks/
│
├── app/
│   ├── main.py                # Entry point for the Bokeh app
│   ├── view.py                # View logic for the app
│   ├── model/                 # Model logic
│   │   ├── mechanisms/        # Folder for MOD files 
│   │   ├── swc/               # Folder for SWC files 
│   │   ├── cells.py           # Logic related to NEURON cells
│   │   ├── model.py           # Core model logic
│   │   └── swcmanager.py      # Manager class for SWC files
│   ├── presenter/             # Presenter logic
│   │   ├── presenter.py       # Main presenter class
│   │   └── ...                # Mixins for the presenter class
│   ├── static/                # Static files (e.g., CSS, JS)
│   └── templates/             # HTML templates for the app
│
├── notebooks/                 # Jupyter notebooks with demos
│   ├── standalone_demo.ipynb  # 
│   └── swc_demo.ipynb         # 
│
├── environment.yml            # Conda environment configuration file
├── requirements.txt           # An alternative for pip
├── README.md                  # Project README
└── LICENSE                    # License file
```

## Installation

### 1. Set Up a Conda Environment (recommended)
Create and activate a conda environment using the provided environment.yml file:

```bash
conda env create -f environment.yml
conda activate dendrotweaks
```

### 2. Install Dependencies Using PIP (optional)

Alternatively, install required packages using pip

```bash
pip install -r requirements.txt
```

## Usage

### Run the Bokeh Server
To run the Bokeh server and launch the app locally, use the following command:

```bash
bokeh serve --show app
```

This will start the Bokeh server and automatically open your default web browser to display the app.

If needed, refer to the official [Bokeh documentation](https://docs.bokeh.org/en/latest/docs/user_guide/server/app.html#ug-server-apps) for additional information.

### Upload a cell

In the left menu select one of the avaliable `.swc` files. The morphology plot and the graph view should appear.

### Upload the mechanisms from a json file

For some models (Park_2019.swc, Poirazi_2003.swc, or Hay_2011.swc), you can upload predefined biophysical parameters. Click the `Import biophys` button in the left menu. The parameters will be applied to the selected model.

### Explore the distribution of ion channels

1. Go the the `Membrane` tab in the right menu.
2. Select a channel conductance (e.g. `gbar_na`) using the `Parameter` dropdown widget. The distribution should be rendered on the graph view.
3. Try to adjust distribution parameters using the sliders.

### Run a simple simulation

1. Go to the `Stimuli` tab in the right menu. 
2. With the soma selected (default), activate the switches for `Record voltage` and `Inject current`. 
3. Adjust the current amplitude using the slider (e.g., 150 pA for `Park_2019.swc`).

### Explore the kinetics of ion channels

1. Click the `Channels` button on top of the right menu. A new menu for exploring channel kinetics should appear.
2. Select a channel using the `Channel` dropdown widget. Plots with channel activation/inactivation curves should appear in the workspace.
3. Try to adjust channel parameters with sliders.
4. Try to standardize the channel model using the `Standardize` button.

## Troubleshooting
DendroTweaks is currently under active development. We are making efforts to ensure stability, and apologize for some issues that may still arise. If you encounter any problems, please try restarting the server. First, stop the server from the console with Ctrl + C. Then restart it using:
```bash
bokeh serve --show app
```


