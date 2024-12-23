#!/bin/bash
echo "Cleaning up previous builds..."
rm -rf build dist
echo "Installing requirements..."
pip install -r requirements.txt
echo "Building application..."
python build.py
echo "Done!" 