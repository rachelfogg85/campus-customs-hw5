# AI Prompts Log — HW5 (Campus Customs Multi-Agent)

This file logs every prompt submitted to the AI assistant for this assignment, verbatim, organized by problem.

## Problem 1: Vine coder prompts

1. I am working in HW5 where we will be making a campus customs multi-agent. Please document all my prompts in AI_prompts.md Confirm you've found the folder and create the AI_prompts.md file

2. thank you! For some background information, don't actually do anything yet:

we are creating a campus customs multi-agent shop. This will be built using an MCP server, FastAPI backend. and a React dashboard. The team will have full connectivity which means that any agent can delegate tasks to any other agent for help. These are the agents we will have:

Boss; reads each ticket and decides who will work on it and make final cuts
Inventory: checks stock by SKU and size, spots shortfalls, and figures out which vendor can restock
Accounting: watches cash and invoices, checks margins, and prepares payments or purchase orders for human approval
Facilities: handle ship space side
Customer Service: draft messages for customers

3. also please make sure AI_prompts is all broken up by problem so all the prompts to date should be included in Problem 1: Vine coder prompts

4. also in terms of rules, I've included data in the HW5 folder and these are the rules:
field desk.date_today is "today" for the shop, use this date to determine what is overdue
Vendor lead times come from the vendors table
a vendor will not ship new products while they have an unpaid invoice
Human approval is required for any payments.
If there is not enough cash, the pay tool must refuse - no negative balances are allowed
Cash only goes out in this homework

5. Before a full run to resolve the tickets, make sure to resit the database to the original values, do not email customers or call real vendors

6. Please make sure gpt-6-luna is the only model used for the agents

## Problem 2: Study the campus customs database

1. Okay we are moving on to Problem 2: Study the campus customs database.

Open the data/campus_customs.db and look through every table and its fields. copy the original file to data/campus_customs_new.db
study the three open tickets so we can see how they link to the other tables

start output/harness.md. For each table list the fields and one short line on why that table matters for the agents

## Problem 3: Build the MCP server

1. For problem 3: Build the MCP server, please write an mcp_server/ using FactMCP. It will talk to data/campus_customs_new.db. Every agent in this homework will use the tools in the MCP server. we will add more tools to it later, for now lets write three tools that we will need for the tickets in the database Never invent any data, only use the information in the database.

in Output/harness.md list each of your three MCP tools. For every tool include: which table it reads, which ticket is helps unlock (101,102,103) and one sentence on why that tool is the right one for the ticket. Vague lines like "reads inventory" score low, tie the tool to the ticket. Also add a short mcp_server/README.md file that explains what the MCP server is for, which database file it uses and the three tools it has

## Problem 4: Connect the MCP server and smoke test

1. Now we will add the MCP server to the project so that you can call the tools. Save the connection JSON text in a .mcp.json at the project root. With the MCP and vibe coder connected, test each of the three MCP tools. Save the evidence in output/mcp_smoke.json

For each tool include:

2. The prompt you asked the vibe coder, the tool name, and the tool output (must match values in data/campus_customs.new.db

3. what are the three tools, can you show me please

4. so all of this should be documented for problem 4: add the mcp server to vibe coder and test each tool

## Problem 5: Build the agent team and grow the MCP tools

1. Build the agentic team for campus customs using PydanticAI: Boss, inventory, accounting, facilities, and customer service. Include prompts, models, and agent loops so they can delegate work to each other with full connectivity.

Put the agent prompts in backend/prompts/ - one file per agent. put data types in backend/models.py and the agent files under backend/ (your layout can vary as long as the five roles are clear). The use your PORTKEY_API_Key and only gpt-6-luna for every agent.

Write each prompt in your own words with the shop rules that agent needs. More detailed prompts that cover all aspects of an agent's work and scope score higher than a short generic prompt

add any tools the agent needs to your mcp server so they can work on the open tickets. shop facts come from the MCP server over data/campus_customs_new.db. Do not invent a second ship-tools layer that bypasses MCP.

Wire the agents so they append to output/audit_trail_json as they run: for each agent loop step, record enough to audit later, append to this file. do not wipe it after each run.

In output/harness.md list each agent and each MCP tool (including ones you add in this problem) along with which table the tool uses. also add a short safety section: the guardrails a real business would want when agents touch real customers and real money, plus limits that keep token use in check. Update mcp_servver/README.md so the tool list matches what you have now

## Problem 6: Plan the three tickets

1. For problem 6: plan the three tickets

before you wire the backend, write down what you expect the team to do on each open ticket. build output/desk_tickets.html - a page you can double-check with one tab per ticket (101,102,103). Also add empty Cash and Reflection tabs for later problems (leave them blank or with a short "coming later" note for now

On each ticket tab, fill an expected section only (leave room for an actual section you will fill after you run the agents)

for each ticket's expected section write in your own words
who the boss should call first and why
all the agent delegations you expect - not boss calls everyone
which mcp tools you expect that run to use

plans that send every specialist on every ticket score low you will compare this plan to what actually happens when your agents resolve the three tickets

## Problem 7: Backend routes

1. For problem 7: backend routes

For the react frontend dashboard that we will make in the next problem, needs a backend it can call. in backend/main.py use FastAPI and add routes that do the following:

1. return the three tickets and whether each is open or resolved
2. Take a ticket id and run your agent team on that ticket
3. return recent agent events - what each agent said and which tools they used, so the board can refresh
4. approve a payment or purchase after a human clicks approve (agents only repare the pay, this route is what actually changes cash)
5. Return the current checking balance from cash_accounts
6. Reset the database to the original values when you want to try a fresh run

From the backend/ folder, start the serve with: uvicorn main:app --reload --port 8000

This turns on your backend at http://localhost:8000 so the frontend dashboard can call those routes. In the output/harness.md list each route in one line (what URL/what it does)

## Problem 8: Agent dashboard

1. Please build the frontend dashboard in frontend/ with React + Vite + TypeScript. The page should call the routes we built in the previous problem (7). At a minimum the board should have the following:

1. list all three tickets
2. Let you pick one ticket and start the agent team on it
3. Show each agent and what they are saying / doing while the ticket runs
4. Mark a ticket resolved when the run finishes
5. Show a short summary of what each agent did on that ticket
6. Let a human approve a pay or purchase when asked
7. Show the checking balance (it should drop after an approved pay)

Make the dashboard look good. Be creative with the layout and feel - this is a real desk people would want to sit at, so put thought into how it should look

Tell the front end to talk to your backend at http://localhost:8000. On the backend, allow the Vite page origin (usually http://localhost:5173) so the browser is allowed to call those routes. Start the board with: npm run dev

This opens the react desk in my browner so i can pick tickets and watch agents.

Write output/design.md with what you chose for the dashboard look (layout, how agents read differently, how resolved tickets and cash show up) and why -  including the creative choices that make it feel special and something humans would actually enjoy using

## Problem 9: Resolve the tickets

1. On the above question should be logged in problem 8: agent dashboard

for problem 9: resolve the tickets
before testing the agents on a full run over the three tickets, reset the working database data/campus_customs_new.db again so you start clean. Note the starting checking balance. then run all three tickets on the board (101,102,103) until each is resolved. Open output/desk_tickets.html from problem 6. On each ticket tab, fill in the actual section from this run: which agents worked, what they delegated, and which tools they used. Keep your expected section so you can compare the two

On the cash tab of the same output/desk_tickets.html, itemize the money:

1. starting checking balance (after the reset)
2. For each ticket: how cash changed when that ticket resolved and why (which pay/purchase, dollar amount)
3. Ending checking balance - it must match cash_accounts in the working database

wrong cash math losses points even if the board shows every ticket resolved. also save:
output/resolved_tickets.json - for each ticket: id, final status, short outcome, what each agent contributed, and any human approvals
output/resolved_board.html - a page you can double-click with a screenshot of your react board for each resolved ticket (101, 102, and 103)

Append real runs to output/audit_trail.json. Finish output/harness.md so it covers tables, MCP tools, the five agents, API routes, the dashboard, and safety rules

## Problem 10: Reflection

1. For problem 10, Open output/desk_tickets.html and fill the reflection tab. Answer in your own vibe and be detailed and thorough:

1.  how would you evaluate the performance of the agents on each ticket and why?
2. for each ticket, how did actual compare to the expected plan you wrote earlier?
3. What would have been simpler as one agent with tools and why?
4. Describe the three new problems Campus customs might face that this agent team could solve with the tools you built?

2. also describe three new problems Campus Customs might face that this agent team could not solve with the tools you build and explain the tools and agents you would need to solve them

3. tie every answer to this app and the three tickets you ran. use the ticket tabs and cash tabs on the same page as your evidence. Generic AI essays without Campus customs details will score low

## Follow-up: finishing Problems 9 and 10

1. can i give you the next task while you do the above?

2. why is it taking so long for ticket 103

3. is the 103 issue resolved?

4. Can you stop that and check what's the issue? It shouldn't be taking this long

5. can i have the link to see where everything is being done?

6. what about the html ?

7. okay i noted also that the actual sections arent complete

8. please make sure to document all of this is AI_prompts,md

9. where is the latest html that shows me everything

10. could you please write up exactly what you did for every question

11. for the design of the html page, i want a white background and i want the text in laymen terms, not too much heavy technical jargon for ease of use and understanding

12. where is the actual agent dashboard which i can press to get the work done?

13. for all the pages i want the backgrounds white with the lines blue instead of pink, and i want this for the the deliverables e.g., htmls and losts

14. my run the agent function isn't working

15. please give me the links again to see the agent and press run

16. why does 101 go to accounting if it is an inventory issue?

17. got it

18. and why does the rent not get backed? why is our checking only $160?

19. but do you see how there is an issue when i go to approve it: [screenshot of Ticket 102's board after a re-run, showing a due-date/balance conflict between the ticket's old notes and the live lease/cash data, and a refused rent payment]

20. and why is #103 blocked? it seems like the same issue as #101, in terms of an overdue payment, does that make sense? is it actually the same issue

21. please make sure all of this documented in AI_Prompts.md

22. why is there text in the middle here: [screenshot showing a delegation_end row dumping the full raw answer as plain unstyled text, right below the same answer already shown in a styled bubble] is there a better way to illustrate this to make it more clear? is this the different agents talking to each other

23. please share the new links so i can see it

24. please indicate who it handed its answer back to [screenshot of a "Customer Service handed its answer back (see its reply above)" delegation row with no recipient named]

25. please give me the updated links

26. where aren't there parameters in the backend API docuents?

27. also it still doesnt specific who it is going back to [screenshot of an "Accounting handed its answer back (see its reply above)" row with no recipient named]

28. also make sure all the design requests I had are included within output/design.md

29. when i say see reset the data why are the steps still available: [screenshot of ticket 101 after clicking "Reset data" — checking balance back to $3,400.00 and status "Open," but the Agent Feed still showing old historical steps from a prior run]

30. okay noted thank you

31. [image: expected file layout for hw5/] okay not i need to push this to be public on Github repository so the graders can clone it. I will need to submit the Repo URL for grading so please put it in output/githubt_url.txt. Do not push the real .env to the Github repo. Do include both database files under data/ (the original and your working copy) so graders can run your app easily. I've included the expected layout in the photo

README should explain: copy original DB to the working copy when you need a clean run, start mcp server, start FastAPI backend, start the reach board, reset the DB before a full three-ticket run
