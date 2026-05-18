# Linear Regression Flask App

The app uses simple linear regression to learn the linear regression. The user enters a study hour value, and the app predicts the exam score.
```text
Input: 5
Output exam score is: 60.5
```

## File Structure

```text
flask_app/
├── models/
│   └── linear_regression_model.joblib
├── templates/
│   └── index.html
├── .gitignore
├── .python-version
├── app.py
├── data.csv
├── README.md
├── requirements.txt
└── train_model.py
```


## First-Time Setup Steps

Run the following commands when setting up the project for the first time on Mac.

### 1. Go to the Project Folder

```bash
cd path/to/flask_app
```
### 2. Create a Virtual Environment

```bash
python3 -m venv .venv
```

### 3. Activate the Virtual Environment

```bash
source .venv/bin/activate
```

## Run the Project

### 1. Train the Model

```bash
python3 train_model.py
```

This creates the saved model file:

```text
models/linear_regression_model.joblib
```

### 2. Run the Flask App

```bash
python3 app.py
```

### 3. Open the App in Browser

Open this link in your browser:

```text
http://127.0.0.1:5000
```

---

## How to Use the App

1. Enter the number of study hours.
2. Click **Predict**.
3. The app will display the predicted exam score.

Example output:

```text
Output exam score is: 72.5
```
