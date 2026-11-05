Video: https://youtu.be/wJKTBl3XFPo?si=9vHEezMv5lXWipb7

My Final Project Mentor is Aadity Sharma, who approved my problem and proposed solution. As a professional pitcher for the Chicago White Sox, I often feel overwhelmed by the extensive scouting reports on opponents filled with statistics and data that are challenging to interpret. My solution is an AI baseball scouting app that generates scouting reports through user input or internet data. A key feature will let users adjust the report complexity, since I prefer simpler summaries that are easier to memorize. Aadity provided valuable feedback, suggesting that I expand the project by exploring various ways to visualize player statistics. I plan to enhance the app to extract and visualize different data types, incorporating heatmaps and other visual tools to simplify scouting insights.

## Problem Decomposition

> **Build a Streamlit Interface**
>
> * **What it does:** Create an easy to use interface for uploading reports, entering pitcher information, and then viewing scouting recommendations. One feature I want is an adjustable slider to set the preferred scouting report length.
> * **Why it matters:** Having a good user interface is essential and will make it easy and quick to generate a scouting report.
> * **Why explore with AI:** Use AI to help design the app on Streamlit.

> **Build Pitcher Profiles**
>
> * **What it does:** Users manually enter in their strengths and weaknesses or can upload pitching reports that automatically populate their profiles.
> * **Why it matters:** Combining statistical data with personal knowledge would provide the model with a complete picture for the pitcher.
> * **Why explore with AI:** Experiment with how effectively the AI can incorporate both uploaded stats and user-provided information, and test if the model will favor one over the other.

> **Upload and Extract Opponent Scouting Reports**
>
> * **What it does:** Allow users to upload opponent scouting reports containing data like written notes, statistical tables, and heatmaps.
> * **Why it matters:** Accurate data extraction is essential to the program because of all the different types of data.
> * **Why explore with AI:** Experiment with different extraction methods, especially for complex tables and heatmaps, and test their accuracy against real scouting reports.

> **Generate Scouting Report with RAG model**
>
> * **What it does:** The system combines information from the user's pitching profile and the opponent scouting reports to generate a specific pitching scouting plan. RAG can retrieve relevant information from uploaded documents. When the app later scrapes data from the internet, the RAG model will become important given the larger knowledge base.
> * **Why it matters:** This is the central feature of the app. Rather than simply summarizing an opponent's weaknesses the application should recommend strategies that match the user's strengths and weaknesses.
> * **Why explore with AI:** Focus on testing different retrieval methods, prompts and scouting report formats. I can use AI to evaluate whether the generated reports reflect both the hitter's statistics and the pitcher's information.

> **Add Interactive Visualizations**
>
> * **What it does:** Display a hitter's tendencies and pitching data through interactive heatmaps and visuals.
> * **Why it matters:** This addresses Aadity's feedback about exploring more ways to represent baseball data. Visualizations are important to represent patterns in data.
> * **Why explore with AI:** Use AI to prototype different charts and visualizations, and give it examples of things you find on the internet.

> **Expand the Application**
>
> * **What it does:** Add user accounts and persistent storage so users can save their profiles and previously generated reports. Automatically be able to scrape the internet using the TrueMedia API (access needed).
> * **Why it matters:** Users shouldn't need to reenter their arsenal or reupload the same documents every time they use the app. This could also create a foundation for a larger, continually updated scouting database.
> * **Why explore with AI:** Use AI to help design the database structure, implement authentication, connect storage, and test whether the saved information is retrieved correctly and the API is used correctly.

## Proposed Work Order

I'm planning to tackle the above tasks in chronological order, breaking them down into smaller steps. First, I will work on the Streamlit App, since it's good to get something visual I can see, then add the backend later. Then I'll work on the Pitcher Profile task, which lets users manually input their pitches and upload their profiles. This leads into the next task: uploading and extracting data from scouting reports. These tasks are doable, and I can show a few iterations for my Journal 2. Once I've completed those three tasks, I can start experimenting with the backend RAG model and begin generating scouting reports.

## List of Questions I Want to Discuss with My Mentor

- How should I contact the different companies that provide baseball data APIs? Are there any best practices you've used?
- At what point will I think that I have something that meets or exceeds standards for the Final Project? I'm so excited about this project that I'm worried I'll end up spending too much time building and tinkering with it.
- If I get to a point where I'm satisfied with the app's ability to do scouting for pitchers, should I consider making the app broader and able to tackle scouting for different aspects of the game or maybe for other sports?



