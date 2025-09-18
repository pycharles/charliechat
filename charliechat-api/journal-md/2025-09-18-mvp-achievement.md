# MVP Achieved

> Big news, the MVP is ready to share! I focused on building, not journaling. I planned to write daily notes. I kept coding instead. I will backfill short entries below.

## Announcement
The MVP is live and ready for feedback. I still have plenty of TODOs. I will ship improvements in small batches. I want real input before I polish the small stuff.

## Costs
$1.20 total for the week. I kept AWS costs tight with deliberate choices and strict limits. I will post a detailed cost breakdown soon. Interestingly, my two highest costs were DNS hosting ($0.50/month per zone — I could have left this with my registrar) and Amazon Lex, which I ultimately removed in favor of handling all logic in Lambda.
&nbsp;  
&nbsp;  


![Cloud Costs Thus Far](/static/journal/2025-09-18_15-AWS-Costs.png)


&nbsp;  
## Key Milestones  

- **Knowledge Base Integration** – Wired in resume context, tuned retrieval to keep responses focused.  
- **Prompt Engineering** – Switched to first-person voice, shortened answers and added follow-up prompts.  
- **Conciseness & Variability** – Introduced character-based targets to avoid truncation while keeping answers natural.  
- **Session Memory** – Added light conversation history so the bot remembers context between questions.  
- **UI & UX Polish** – Designed a clean, focused chat interface, improved layout and readability, minimized visual clutter and added voice style controls for a fun user experience.  
- **Infrastructure-as-Code Deployment** – Defined and provisioned AWS resources with Terraform, creating a reproducible and scalable deployment foundation for future growth.  
- **Architecture Simplification** – Consolidated intent handling into a single FastAPI-based Lambda, removing Lex as a dependency for a simpler, faster and fully local development flow.
- **Logging & Observability** – Added structured logging with timestamps and response timing to improve troubleshooting and performance monitoring.  
- **Testing Foundation** – Set up pytest with coverage and async testing to catch regressions early and prepare for automation.  
- **Content & Persona Design** – Refined Charlie Chat’s tone, voice style options and personality for a recruiter-ready, interactive experience.  
- **Security & Environment Management** – Implemented `.env` handling and secure secret management for local/prod consistency and safer development.  
- **Documentation** – Updated README and developer notes to make the project reproducible and easy to understand for future contributors or hiring managers.  
- **Cost Discipline** – Logged token usage, setup an AWS Budget, stayed with on-demand models and removed Lex to simplify architecture, have more control and save money.  


## What's next?  Tell me what you think!
I want your feedback. Try the site. Break it if you can. Tell me what felt smooth and what did not.  

Feel free to either email me or use the feedback form.  
