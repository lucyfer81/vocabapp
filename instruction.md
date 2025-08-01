# VocabApp: Standard Development and Deployment Workflow

This document outlines the standard procedure for developing new features and deploying them to the production environment. Following these steps ensures that the production service is never directly affected by development work and that all changes are version-controlled.

## Core Concepts

- **Production Directory**: `/home/ubuntu/PyProjects/vocabapp`
  - **Purpose**: Runs the live application.
  - **Git Branch**: Always on `main`.
  - **Action**: Only ever `git pull` and restart the service here. **NEVER EDIT CODE HERE.**

- **Development Directory**: `/home/ubuntu/PyProjects/vocabapp-dev`
  - **Purpose**: All development, coding, and testing happens here.
  - **Git Branch**: `develop` or a `feature/*` branch.
  - **Action**: This is your workspace.

- **Branches**:
  - `main`: Represents the stable, live production code. It only receives updates from the `develop` branch when a release is ready.
  - `develop`: The primary development branch. It contains the latest (potentially unstable) features. All new feature branches are created from `develop`.
  - `feature/*`: Temporary branches for specific new features (e.g., `feature/user-profiles`). They are created from `develop` and merged back into `develop`.

---

## Phase 1: Developing a New Feature

**Goal**: To build a new feature in isolation without affecting other development or production.

1.  **Navigate to the Development Directory**:
    ```bash
    cd /home/ubuntu/PyProjects/vocabapp-dev
    ```

2.  **Sync with Remote Repository**:
    Ensure you have the latest changes from GitHub on all branches.
    ```bash
    git pull origin
    ```

3.  **Switch to the `develop` Branch**:
    Make sure you are starting from the main development line.
    ```bash
    git checkout develop
    ```

4.  **Create a New Feature Branch**:
    Name it descriptively.
    ```bash
    # Example: git checkout -b feature/add-quiz-mode
    git checkout -b feature/your-new-feature-name
    ```

5.  **Code, Code, Code**:
    - Make all your code changes for the new feature.
    - Run the local development server to test your changes:
      ```bash
      export FLASK_CONFIG=development
      flask run --debug
      ```
    - Remember, this uses the `dev-wordbook.db` database, so it's safe to add test data.

6.  **Commit Your Changes**:
    Commit your work frequently with clear messages.
    ```bash
    git add .
    git commit -m "feat: Implement the first part of the quiz mode"
    ```

7.  **Push Your Feature Branch to GitHub**:
    This backs up your work and prepares it for a Pull Request.
    ```bash
    # Example: git push -u origin feature/add-quiz-mode
    git push -u origin feature/your-new-feature-name
    ```

---

## Phase 2: Merging a Feature

**Goal**: To merge your completed feature into the main `develop` branch.

1.  **Open a Pull Request (PR) on GitHub**:
    - In your browser, go to your GitHub repository.
    - GitHub will likely show a prompt to create a Pull Request from your new feature branch.
    - Set the base branch to `develop` and the compare branch to your `feature/*` branch.
    - **`feature/your-new-feature-name` -> `develop`**
    - Fill in the details and create the PR.

2.  **Review and Merge**:
    - Review the changes in the PR.
    - Once satisfied, click "Merge Pull Request".
    - You can safely delete the feature branch after merging.

---

## Phase 3: Deploying to Production

**Goal**: To release the stable features from `develop` into the live `main` branch and update the production server.

1.  **Open a Pull Request from `develop` to `main`**:
    - On GitHub, create a new Pull Request.
    - This time, set the base branch to `main` and the compare branch to `develop`.
    - **`develop` -> `main`**
    - This PR represents a "release". Give it a title like "Release Version 1.1".

2.  **Merge the Release PR**:
    - After confirming all features in `develop` are stable and ready for production, merge the PR.
    - Your `main` branch on GitHub now contains the latest production-ready code.

3.  **Update the Production Server**:
    - SSH into your server.
    - Navigate to the **PRODUCTION** directory:
      ```bash
      cd /home/ubuntu/PyProjects/vocabapp
      ```
    - Pull the latest version of the `main` branch from GitHub:
      ```bash
      git pull origin main
      ```
    - **Restart the Application Service**:
      Use the command you have set up to restart `waitress` (e.g., `sudo systemctl restart vocabapp` or similar).

Your new features are now live!
