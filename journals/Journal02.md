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





AI Policy: You may not use AI to write your journal or create your video. You may work with an AI to come up with a decomposition of your project (see the second bullet under (2)). You may certainly use AI to build your prototype and tests for it (see (3)).

1. Invite your TF mentor to be a collaborator on your GitHub repository. They shared their GitHub username with you in their feedback on your first journal. (Completed)

2. In your journals folder, create a Markdown file named Journal02.md and respond to the following prompts in no longer than 700 words: (Completed)

3. If your mentor gave you feedback that asked you to adjust your problem statement, please begin your journal with your reformed problem statement. (N/A)

4. With a decomposition of your project into reasonably sized tasks, explain why each task is something you can specify or explore through iteration with an AI.

5. Place your decomposed tasks into an ordered work schedule, without dates. You may state that you're planning to work on one or two tasks in parallel. Explain why you chose this order. For example, are you starting with the simplest piece, or the one you are most excited about? Or, is there some piece that you think needs to be done before you can make progress on other pieces?

6. Write a list of questions you’d like to discuss with your mentor.

7. Prototype one task from your decomposition and test it. Record a video (3 minutes maximum) demonstrating your prototype. Include a link to the video at the top of your journal. Set the link's permissions so that anyone with the link can view it.
Add, commit, and push your code and journal to your repo, so that the teaching staff can see the progress that you wrote about. 
Submit your journal to the corresponding assignment on Gradescope.

Journal 2 Written Response: 
*   If your mentor gave you feedback that asked you to adjust your problem statement, please begin your journal with your reformed problem statement.
*   With a decomposition of your project into reasonably sized tasks, explain why each task is something you can specify or explore through iteration with an AI.
*   Place your decomposed tasks into an ordered work schedule, without dates. You may state that you're planning to work on one or two tasks in parallel. Explain why you chose this order. For example, are you starting with the simplest piece, or the one you are most excited about? Or, is there some piece that you think needs to be done before you can make progress on other pieces?
*   Write a list of questions you’d like to discuss with your mentor.

My Final Project Mentor is Aadity Sharma, and in her feedback to me I was given the clear to proceed with my problem and preposed solution. My problem I've decided to continue with was  solution that I'm working on for my Final Project is a AI baseball scouting app, where users would be able to generate AI scouting reports on Opponents either through user input data or data scraped from the internet. The main aspect of the 


> **Build a Streamlit Interface**:
*   **What it does:** Create an easy to use interface for uploading reports, entering pitcher information, and then viewing scouting recommendations.
*   **Why it matters:** Having a good user interface is essential for the App because any pitcher could just put an opponent scouting report and a report on themselves into ChatGPT and get a usual scouting report. The user interface will differentiate this from ChatGPT
*   **Why explore with AI:** Use AI to help design the app on Streamlit, and in later iterations I can have AI build me the App in JavaScript, HTML, and CSS, and make Python the backend for the chatbot
> **User Upload Profiles**:
*   **What it does:** Users can upload files about themselves, and the Program could interpret the information 
*   **Why it matters:** These reports can automatically populate the pitcher's profile and provide additional statistical information for the program without relying on manual data entry from the user
*   **Why explore with AI:** I can test different document extraction approaches and refine how the app interprets tables and charts. I can work on this simultaneously with the next decomposed step, because the opponent reports and user reports will be extracted similarly.
> **User Built Profiles**:
*   **What it does:** Users can build their profiles manually: add their pitches, arsenal, and strengths.
*   **Why it matters:** Uploaded reports on the user may not include personal preferences or strengths of the user. A report on a pitcher can only say so much, so it makes sense to let the user tell the program what their strengths are. 
*   **Why explore with AI:** I can iterate on the profile interface, experiment with different input fields, and test whether the AI incorporates subjective pitcher knowledge appropriately when making recommendations. 
> **Upload and Extract Scouting Reports**: 
*   **What it does:** Users can upload different data formats, and the program can read and organize the information. Here are some examples of scouting reports that my coaches have given me: Written Scouting Notes (I think this is easy to extract), Statistical Table (data extraction is easy, but the dataset needs to be associated with the correct hitter), and Heatmaps (visually stored, so this makes extraction complicated; may need a vision-capable AI model)
*   **Why it matters:** This piece is vital to the program. Collecting different types of data is hard and a very capable task for AI; however, enabling the program to view and interpret heatmaps may be complicated. AI will be essential to writing a program that can interpret and extract these vastly different forms of data
*   **Why explore with AI:** Using AI, I can experiment with different extraction methods; I would also test against real scouting reports 
> **Generate Scouting Report with RAG model**:
*   **What it does:** The system combines information from the user’s pitching profile and the opponent scouting reports to generate a specific pitching scouting plan. RAG can retrieve relevant information from uploaded documents. When the app later scrapes data from the internet, the RAG model will become important given the larger knowledge base. 
*   **Why it Matters:** This is the central feature of the app. Rather than simply summarizing an opponent’s weaknesses the application should recommend strategies that match the user's strengths and weaknesses.
*   **Why Explore with AI:** Focus on testing different retrieval methods, prompts and scouting report formats. I can use AI to evaluate whether the generated reports reflect both the hitter’s statistics and the pitcher's information.
> **Add Adjustable Analysis Depth**
*   **What it does:** Users choose how detailed their scouting reports should be, on a scale of brief and memorable to extensive statistical breakdowns
*   **Why it matters:** Different pitchers want different amounts of information. For example, I like very short memorable scouting reports were as I’ve known other pitchers to be very analytical with their scouting.
*   **Why explore with AI:** Experiment with different prompts and output formats to determine if the AI can consistently generate different levels of detail without losing important informations.
> **Add interactive Visualizations**
*   **What it Does:** Display a hitters tendencies and pitching data through interactive heatmaps, pitch-location charts, and statistical comparisons. For example one possible feature could be Face a Hitter, where I could digitally face a batter, test out different pitch locations and types and have simulated results based on hitter’s data. This could be easier to learn sequencing for scouting a team.
*   **Why it matters:** Visualizations can communicate patterns more effectivily than large statistical tables. This also addresses Aadity’s feedback about exploring more ways to represent baseball data.
*   **Why explore with AI:** Use AI to prototype different charts and visualizations, give it examples of things you find on the internet and test on whether the visuals accurately represent the underlying data.





Problem Decomposition:
*   Build a Streamlit Interface: Create a user-friendly interface for uploading reports, entering pitcher information and then viewing scouting recommendations
*   Upload and Extract Scouting Reports: Be able to upload different formats of data and the program is able to read and organize the information. Types of of infromation uploaded: Written Scouting Notes (easy to extract), Statistical Table (need to be associated with the correct hitter), and Heatmaps (visually stored so complicated, may need vision-capable AI model)
*   Generate personalized AI scouting Reports based on a RAG model
*   Add Adjustable Analysis Depth
*   Add interactive Visualizations
*   Integrate TrueMedia API and make data retrieval automatic
*   Create an App where users can create profiles, store scouting reports, upload Data or just have it automatically scrapped from Truemedia and other sites. 



My Final Project Mentor is Aadity Sharma
Here is her feedback she gave me following Journal01

Hi Truman,

I will be your final project mentor in CS 1066. This means that I will be the go-to person for questions about your project. As always, you can use Ed or speak with any TF with general questions, but for questions about your FP, it is best if you direct them to me since I’ll have the context for what you’re doing. I will also grade your journals and final submission. I am excited to help as you build your project!

**IMPORTANT:** Please invite me as a collaborator to your Github repository by the time of your next journal submission. My username is Abstract-Data-Type.

I attend the Thursday 2:15pm and Thursday 5:15pm sections, so come talk to me any time about your project. We can also meet outside of class -- just email me at aaditysharma@g.harvard.edu to coordinate that.

Great idea and extremely relevant to a core group of high-powered users. I enjoyed reading your report and look forward to seeing you progress towards this idea towards the rest of the semester. As we spoke in class, would love to see the scope of the project expanded to different wats of visualizing and representing inferences about players and their statistics.
Please let me know if you have any questions about this feedback. Keep in mind that the next milestone, FP Journal 2, is due on November 1st.

Best,
Aadity

### Final Project Mentor

My final project mentor is Aadity Sharma. I have added her as a collaborator to my GitHub repository.

### Mentor Feedback

Aadity thought my project was relevant to a core group of highly specialized users. She encouraged me to expand the scope of the project by exploring different ways to visualize and represent inferences about baseball players and their statistics.

### Changes and Ideas Based on Feedback

- **Adjustable scouting report depth:** I want users to control how detailed the reports generated by the AI-scout are. For example, like a slider that could allow users to switch between a report that is consise and just a few bullet points to a complete statistical breakdown. 

- **Different forms of data visualization:** Rather than only displaying written scouting reports, I want to experiment with different ways to represent player statistics and matchup tendencies. This could include strike-zone heatmaps, pitch-type comparisons, and charts displaying hitter strengths and weaknesses.

- **Focus on pitching initially:** I plan to begin with scouting reports designed for pitchers because this is the area where I have the most experience and can best evaluate the accuracy and usefulness of the AI's recommendations. But as Aadity pointed out in her feedback, I should plan on expanding the scope, maybe the final app would just be AI baseball scout where a user could generate an AI scouting report for any opponent, like a hitter could get a scouting report on a pitcher they're facing, or a coach could get a scouting report on a teams hitters so they know where to position their fielders.

- **Expand to both sides of the matchup:** Eventually, I would like the application to generate reports for both pitchers facing hitters and hitters facing pitchers.

- **Automatic scouting data retrieval:** Ideally, users would be able to search for an opposing team or player and have the application automatically retrieve the relevant data. I am currently investigating the possibility of accessing TruMedia Baseball through an API. Until then, I plan to build the application around uploaded scouting reports.



Feedback Summerized: Great product for a "core group of high-powered users." Want the scope of the project to be expanded to different was to visualize and represent scouting reports on players and their stats.
Changes to the Project:
*   This app will ask will be able to display scouting reports that are as detailed as the user wants them so maybe theres a slider that the user can adjust so that it changes the specificity of the AI's response
*   There will be options for different levels of data to be displayed. 
*   This app will start as just something applicable to pitching scouting reports because that knowellege base i'm very comftable with it
*   I then want the app to hadle reports from both ways, pitch hitter and hitter pitcher. I want the site to be able to automatically search up reports on opponents rather than the user having to input them 

> Problem Decomposition:
*   The final goal for the final product would be an app with a chat bar and you can ask what team you're facing and what kind of information you want and the AI would be able to retieve that data from TrueMedia baseball, which is a very large database on ametur and professional baseball statistics, through an API key. I need to contact my professional team, the Chicago White Sox and/or a representative from TrueMedia to get access.
*   Make a user interactive Streamlit app that takes in a user file and an opponent file and is able to generate a scouting report. 
*   The report will have statements that when clicked on give the user explination for the AI's thinking. 
*   