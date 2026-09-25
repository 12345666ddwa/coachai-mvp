# -*- coding: utf-8 -*-
"""Build CoachAI question bank: 2025 HSC Enterprise Computing (NESA official).
Sources:
  - Question stems: official NESA online past exam (fam.hsconline.nesa.nsw.edu.au), 2025 HSC Enterprise Computing
  - Marking guidelines & sample answers: 2025-hsc-enterprise-computing-mg.pdf (NESA, official)
  - Sample full-mark responses: enterprise-computing-2025-full-mark-samples.PDF (NESA, official)
All criteria / sample answers transcribed verbatim from the official marking guidelines PDF.
"""
import json, os

SRC = ("2025 HSC Enterprise Computing (NESA official HSC past exam & marking guidelines). "
       "Paper (online exam): https://fam.hsconline.nesa.nsw.edu.au/ (2025 HSC Enterprise Computing). "
       "Marking guidelines PDF: https://www.nsw.gov.au/sites/default/files/noindex/2025-11/2025-hsc-enterprise-computing-mg.pdf . "
       "Sample full-mark responses PDF: https://www.nsw.gov.au/sites/default/files/noindex/2026-08/enterprise-computing-2025-full-mark-samples.PDF . "
       "Note: Enterprise Computing is examined online; the 2025 paper is the subject's first HSC exam (no 2023/2024 papers exist).")

Q = []

def add(qid, text, marks, mg, topics, sample=None):
    Q.append({
        "id": qid,
        "text": text,
        "marks": marks,
        "marking_guidelines": mg,
        "sample_answers": sample if sample is not None else [],
        "topics": topics,
    })

# ---------------- Q11 (2 marks, intelligent systems - forward chaining) ----------------
add(
 "ec2025-q11",
 "Which of the following is TRUE about forward chaining?\nSelect all that apply.\n"
 "It is generally used when facts are known in advance.\n"
 "It is a reasoning method used by the inference engine.\n"
 "It is generally used when there are multiple possible outcomes.\n"
 "It can be used with backward chaining within the same system.\n"
 "It is a goal-driven approach which finds facts to support a conclusion.",
 2,
 [{"band": "2", "criteria": "Identifies true or false correctly for all FIVE checkboxes"},
  {"band": "1", "criteria": "Identifies true or false correctly for FOUR of the five checkboxes"}],
 ["intelligent systems", "forward chaining"],
 ["Statements that are TRUE (per NESA official answers): "
  "(1) It is generally used when facts are known in advance. "
  "(2) It is a reasoning method used by the inference engine. "
  "(3) It can be used with backward chaining within the same system."],
)

# ---------------- Q14 (3 marks, data science - forms of alternate data) ----------------
add(
 "ec2025-q14",
 "A company wants to analyse memes on social media to assess the effectiveness of its advertising campaign.\n\n"
 "Describe how memes can be analysed to provide insights into the effectiveness of the advertising campaign.",
 3,
 [{"band": "3", "criteria": "Describes how memes can be analysed to provide insights into the effectiveness of the advertising campaign"},
  {"band": "2", "criteria": "Outlines how memes can be analysed to provide insights into the effectiveness of the advertising campaign"},
  {"band": "1", "criteria": "Provides some relevant information"}],
 ["data science", "alternate data", "data analysis"],
 ["The frequency and spread of memes can be quantified to gauge engagement and the advertising campaign's viral impact. Technologies such as data mining tools can be used to identify patterns, trends, and the reach of memes, helping the company understand the campaign's impact.",
  "Answers could include: Memes can be analysed qualitatively to understand customer perceptions by examining their themes, tone and attitude."],
)

# ---------------- Q15 (a) 2 marks, relational database ----------------
q15_scenario = (
 "The following are three tables from an IT company's relational sales database.\n\n"
 "Customers\n  CustID | FirstN | LastN | Email | Phone\n"
 "  001 | Abraham | Li | a.li@example.com | 555-0101\n"
 "  002 | Sophia | Smith | s.smith@example.com | 555-0102\n"
 "  003 | Priya | Singh | p.singh@example.com | 555-0103\n\n"
 "Products\n  ProdID | ProdN | Category | Price | Quantity\n"
 "  LP1 | Laptop | Electronics | 1200 | 30\n"
 "  OC31 | Office Chair | Furniture | 200 | 20\n"
 "  HP43 | Headphones | Electronics | 150 | 100\n"
 "  SP5 | Smartphone | Electronics | 800 | 50\n\n"
 "Sales\n  SaleID | CustID | ProdID | SaleDate | Quantity | TotalCost\n"
 "  1 | 001 | LP1 | 17-01-2025 | 1 | 1200\n"
 "  2 | 002 | SP5 | 16-01-2025 | 2 | 1600\n"
 "  3 | 001 | HP43 | 15-01-2025 | 3 | 450\n"
 "  4 | 003 | OC31 | 18-01-2025 | 1 | 200\n"
 "  5 | 003 | OC31 | 14-01-2025 | 2 | 400\n"
 "  6 | 002 | SP5 | 18-01-2025 | 1 | 800"
)
add(
 "ec2025-q15a",
 q15_scenario + "\n\n(a) Use the dropdown lists provided to identify the correct key types, and the relationship "
 "types between tables. (2 marks)\nPK = Primary key, FK = Foreign key.\n"
 "For each field in the three tables (e.g. Customers.CustID, Sales.SaleID, Sales.CustID, Products.ProdID, "
 "Sales.ProdID), select PK or FK; and for the relationships Customers–Sales and Sales–Products select the "
 "cardinality (1 or many).\n[Note: the dropdown selection is performed interactively in the official online exam: https://fam.hsconline.nesa.nsw.edu.au/]",
 2,
 [{"band": "2", "criteria": "Correctly completes ALL the dropdowns"},
  {"band": "1", "criteria": "Correctly completes FOUR of the dropdowns"}],
 ["data science", "relational database", "primary key / foreign key"],
)
add(
 "ec2025-q15b",
 q15_scenario + "\n\n(b) Write an SQL query to display all sales from the electronics category prior to "
 "17-01-2025 in ascending date order, including LastN, ProdN, SaleDate and TotalCost. (4 marks)\n"
 "[Note: the exam provides a runnable SQL sandbox (Run DB), visible in the official online exam.]",
 4,
 [{"band": "4", "criteria": "Provides a correct SQL query"},
  {"band": "3", "criteria": "Provides a SQL query that addresses most of the requirements"},
  {"band": "2", "criteria": "Shows some understanding of the problem or SQL"},
  {"band": "1", "criteria": "Provides some relevant information"}],
 ["data science", "SQL", "relational database"],
 ["SELECT ProdN, SaleDate, TotalCost, LastN\nFROM Customers, Products, Sales\nWHERE Customers.CustID = Sales.CustID\nAND Products.ProdID = Sales.ProdID\nAND Products.Category = 'Electronics'\nAND Sales.SaleDate < '17-01-2025'\nORDER BY SaleDate ASC"],
)

# ---------------- Q16 (a/b, intelligent systems) ----------------
q16_scenario = (
 "A TV manufacturer wants to improve the efficiency and reliability of its manufacturing system. It plans to "
 "incorporate an intelligent system into its manufacturing process to collect live data for analysis. Hardware "
 "devices will be installed to collect data on the system's operations. The data is then sent to a server for "
 "processing.\n\nThe manufacturing processes include attaching the LCD panel to the motherboard and testing the "
 "brightness of the screen. The current system is controlled through manual processes and monitoring."
)
add(
 "ec2025-q16a",
 q16_scenario + "\n\n(a) Describe the hardware that is needed for the intelligent system. Include examples of "
 "specific types of sensors in your answer. (4 marks)",
 4,
 [{"band": "4", "criteria": "Describes hardware needed for the intelligent system; Includes examples of specific types of sensors"},
  {"band": "3", "criteria": "Outlines relevant hardware devices; Includes at least ONE sensor"},
  {"band": "2", "criteria": "Outlines ONE relevant hardware device OR identifies relevant hardware devices"},
  {"band": "1", "criteria": "Provides some relevant information"}],
 ["intelligent systems", "hardware", "sensors"],
 ["Different types of sensors will be needed for the intelligent system and cameras can be used to collect visual information about the TV screens for quality assurance. Vibration and proximity sensors can be used to detect issues with the machinery, to potentially prevent a breakdown from occurring. Light sensors can be utilised to measure the brightness of the screens during the testing phase of manufacturing.\nAll sensors will need to be connected to the intelligent system via a network. The networking hardware could include switches, routers, servers, and transmission media such as Wi-Fi and ethernet cables.",
  "Answers could include: Temperature sensors – environment; Pressure sensors – adhesion of screens; Power regulation sensors."],
)
add(
 "ec2025-q16b",
 q16_scenario + "\n\n(b) Explain the potential benefits of introducing an expert system into the manufacturing "
 "process. Support your answer with reference to Industry 4.0. (4 marks)",
 4,
 [{"band": "4", "criteria": "Explains potential benefits of introducing an expert system into the manufacturing process, with reference to Industry 4.0"},
  {"band": "3", "criteria": "Outlines potential benefits of introducing an expert system into the manufacturing process"},
  {"band": "2", "criteria": "Outlines ONE potential benefit of introducing an expert system OR ONE feature of Industry 4.0"},
  {"band": "1", "criteria": "Identifies potential benefits of introducing an expert system and/or features of Industry 4.0; Provides some relevant information"}],
 ["intelligent systems", "expert systems", "Industry 4.0"],
 ["Integrating an expert system into the TV manufacturing line upgrade would bring several benefits, in line with Industry 4.0 concepts. The expert system would be able to predict when maintenance is needed, by analysing sensor data. The system would be able to alert staff before an issue arises, and therefore minimise downtime.\nQuality control of the TVs would be improved as the expert system would be able to find defects in the TVs better than a human could, by using algorithms and sensor data, as it can detect subtle issues and prevent defects reaching the end of the line. This links with Industry 4.0's focus on precision, reducing waste and improving product quality."],
)

# ---------------- Q17 (a/b, data science/data visualisation) ----------------
q17_scenario = (
 "A coffee shop chain has branches in all major cities in Australia. It collects a large volume of sales data as "
 "well as geographic and demographic data from each of its coffee shop branches.\n\nThe chain plans to use a "
 "cloud-based data warehouse for storage and for future analysis."
)
add(
 "ec2025-q17a",
 q17_scenario + "\n\n(a) Explain how the use of data warehousing could benefit this coffee shop chain. (3 marks)",
 3,
 [{"band": "3", "criteria": "Explains how the use of data warehousing could benefit the coffee shop chain"},
  {"band": "2", "criteria": "Outlines how the use of data warehousing could benefit the coffee shop chain OR identifies features of data warehousing"},
  {"band": "1", "criteria": "Identifies a feature of data warehousing"}],
 ["data science", "data warehouse"],
 ["The coffee shop chain can use data warehousing platforms to its benefit to store and process large volumes of data, expanding storage as needed, to handle high amounts of sales, demographic and other important data. By integrating a variety of data sources, the coffee shop chain can store both structured data and unstructured data in the one place. The data stored in the data warehouse would enable the coffee shop chain marketing team to identify seasonal trends and changes."],
)
add(
 "ec2025-q17b",
 q17_scenario + "\n\n(b) Explain how the advancement of hardware can affect the processing of data from the "
 "data warehouse for this coffee shop chain. (3 marks)",
 3,
 [{"band": "3", "criteria": "Explains how the advancement of hardware can affect the processing of data from the data warehouse for the coffee shop chain"},
  {"band": "2", "criteria": "Outlines how the advancement of hardware can affect the processing of data from the data warehouse for the coffee shop chain OR identifies advancements in hardware that can affect the processing of data from the data warehouse"},
  {"band": "1", "criteria": "Provides some relevant information"}],
 ["data visualisation", "evolution of hardware", "data processing"],
 ["The CPUs used in the data warehouse servers will allow the coffee shop chain to quickly process large amounts of sales and demographic data, enabling faster decision-making. Advancements in storage such as faster RAM and Solid-State Disk drives can provide more secure and efficient ways to store vast amounts of data.\nBetter communication media such as fibre optics enable quicker sharing and online processing of data, to ensure that the coffee shop chain can access the latest information from each branch in real-time."],
)

# ---------------- Q18 (4 marks, spreadsheet features) ----------------
add(
 "ec2025-q18",
 "A small car rental business, with five vehicles, wants to use a spreadsheet to keep track of its bookings.\n\n"
 "A staff member will enter the driver's name, vehicle size selected (small, medium, large), and the number of "
 "days of rental for each vehicle.\n\nThe spreadsheet should automatically provide the following information:\n"
 "• daily rate – small ($200), medium ($250), large ($300)\n"
 "• discount – a discount of 20% is allowed if the booking is for at least 7 days\n"
 "• rental cost – calculated by multiplying the daily rate and the number of days, and allowing for a discount "
 "if applicable.\n\nPart of the spreadsheet has been set up. Complete the spreadsheet so that the required "
 "information will automatically be displayed when rentals are entered.\n"
 "[Note: the exam embeds an interactive spreadsheet (partially pre-filled), visible in the official online exam: https://fam.hsconline.nesa.nsw.edu.au/]",
 4,
 [{"band": "4", "criteria": "Completes the spreadsheet, addressing all the requirements – allows input of driver's name and number of days; allows input or selection of vehicle sizes; automatically generates daily rate, discount and rental cost"},
  {"band": "3", "criteria": "Completes the spreadsheet, addressing most of the requirements"},
  {"band": "2", "criteria": "Provides some correct information and an appropriate formula for the spreadsheet"},
  {"band": "1", "criteria": "Provides some relevant information"}],
 ["data science", "spreadsheet features", "spreadsheet formulas"],
 ["N/A (the official full-mark sample is a spreadsheet input/output screenshot with no textual reference answer; see the official sample full mark responses PDF)"],
)

# ---------------- Q19 (3 marks, UI design) ----------------
add(
 "ec2025-q19",
 "An education business intends to provide a subscription service to teachers and students for online resources. "
 "To register, the subscriber needs to provide their name, email address and date of birth, and indicate whether "
 "they are a teacher or student.\n\nDesign a user interface for registering an account. Clearly label all features.",
 3,
 [{"band": "3", "criteria": "Designs a user interface suitable for registering an account, with features labelled"},
  {"band": "2", "criteria": "Designs a user interface with some relevant features"},
  {"band": "1", "criteria": "Provides some relevant information"}],
 ["enterprise project", "prototypes", "user interface design"],
 ["N/A (the official full-mark sample is a user-interface design image with no textual reference answer; see the official sample full mark responses PDF)"],
)

# ---------------- Q20 (3 marks, data visualisation - spreadsheet features) ----------------
add(
 "ec2025-q20",
 "A marine biologist uses a spreadsheet to analyse past data such as water temperature, pollution levels and "
 "availability of food to predict fish population trends.\n\nDescribe spreadsheet features that can assist the "
 "marine biologist to better understand the datasets visually.",
 3,
 [{"band": "3", "criteria": "Describes spreadsheet features that can assist the marine biologist to better understand the datasets visually"},
  {"band": "2", "criteria": "Outlines ONE spreadsheet feature that can assist the marine biologist to better understand the datasets visually OR identifies spreadsheet features that can assist the marine biologist"},
  {"band": "1", "criteria": "Provides some relevant information"}],
 ["data visualisation", "spreadsheet features and visualisations"],
 ["Spreadsheet features such as charts and graphs can help the marine biologist make informed decisions by visualising raw data, such as changes in water temperature. They can use this to predict the impact on fish populations. Conditional formatting highlights critical data, such as areas where populations are declining by using colours, making it easier to identify trends. Together, these features simplify data interpretation and enhance the presentation of future scenarios."],
)

# ---------------- Q21 (5 marks, DFD) ----------------
add(
 "ec2025-q21",
 "An online booking system allows customers to purchase tickets to a concert. Once a customer specifies the "
 "number of tickets required, the system displays the seats available and allows the customer to make seat "
 "selections.\n\nThe selected seats are held for five minutes for the customer to proceed to payment. The system "
 "displays the total cost and allows the customer to pay using their credit card.\n\nAfter payment is confirmed "
 "by the bank, a digital ticket is generated and sent to the customer. The seat booking database is also "
 "updated.\n\nConstruct a data flow diagram (DFD) to represent this system.",
 5,
 [{"band": "5", "criteria": "Constructs a substantially correct data flow diagram including all relevant external entities, processes, data storage and data flows"},
  {"band": "4", "criteria": "Constructs a data flow diagram that addresses most of the aspects of the system"},
  {"band": "3", "criteria": "Constructs a data flow diagram that includes some aspects of the system"},
  {"band": "2", "criteria": "Provides a diagram that shows some understanding of the problem OR identifies the key components of a data flow diagram"},
  {"band": "1", "criteria": "Provides some relevant information"}],
 ["enterprise project", "data flow diagrams"],
 ["N/A (the official full-mark sample is a DFD drawing with no textual reference answer; see the official sample full mark responses PDF)"],
)

# ---------------- Q22 (a/b, enterprise project / data security) ----------------
q22_scenario = (
 "An insurance company hires a project team to develop a system that manages the personal information of "
 "customers and employees, customer claims and business contracts. The data will be stored and accessed on a "
 "cloud-based server and backed up locally."
)
add(
 "ec2025-q22a",
 q22_scenario + "\n\n(a) Outline a tool that can be used by the project team to manage the project. (2 marks)",
 2,
 [{"band": "2", "criteria": "Outlines a tool that can be used by the project team to manage the project"},
  {"band": "1", "criteria": "Identifies a suitable tool or a feature of project management"}],
 ["enterprise project", "project management tools"],
 ["A Gantt chart can be utilised to organise project timing and development, define tasks to be completed, track and plan progress, and to map staff responsibilities."],
)
add(
 "ec2025-q22b",
 q22_scenario + "\n\n(b) Justify TWO methods that the company can use to maintain the security of the data. "
 "(3 marks)",
 3,
 [{"band": "3", "criteria": "Justifies TWO methods that the company can use to maintain the security of the data"},
  {"band": "2", "criteria": "Outlines TWO methods that the company can use"},
  {"band": "1", "criteria": "Identifies ONE method that the company can use"}],
 ["data visualisation", "data security"],
 ["Staff across the insurance company will be provided with different access levels to the data within the company. Supervisors will have greater access to customer and employee details. For example, supervisors can access historical data and finalise claims, whereas entry level staff may only see individual claim cases. This ensures employees only access data relevant to their roles.\nA customer can access their insurance claim from the cloud-based server. This will require a username and password to be entered and this would be encrypted during transmission. The data will not be understood if intercepted, ensuring privacy and security of customer data."],
)

# ---------------- Q23 (a/b, data visualisation) ----------------
q23_scenario = (
 "As a result of advancements in technology, a company now presents employee performance information on a "
 "dashboard that is updated using real-time data, rather than spreadsheets. The data dashboard is shown.\n"
 "[Note: the dashboard image is exam stimulus material, visible in the official online exam: https://fam.hsconline.nesa.nsw.edu.au/]"
)
add(
 "ec2025-q23a",
 q23_scenario + "\n\n(a) Describe how advancements in software have empowered data analytics. In your answer, "
 "refer to the scenario. (3 marks)",
 3,
 [{"band": "3", "criteria": "Describes how advancements in software have empowered data analytics, with reference to the scenario"},
  {"band": "2", "criteria": "Outlines ONE advancement in software that has empowered data analytics OR identifies advancements in software that affect data analytics"},
  {"band": "1", "criteria": "Provides some relevant information"}],
 ["data visualisation", "evolution of software", "data analytics"],
 ["Advancements in software have transformed data analytics by enabling faster processing of large datasets, automation, real-time insights and enhanced visualisation. In the scenario, the company moved from static spreadsheets to dynamic dashboards, which will allow users to uncover patterns and trends that might have gone undetected in the past. These dashboards enable users to drill down into a specific area of interest without requiring programming skills. They also assist in improving decision-making by presenting trends, comparisons and key performance indicators clearly."],
)
add(
 "ec2025-q23b",
 q23_scenario + "\n\n(b) Explain how the visualisations used in the data dashboard provided could affect the "
 "management team's user experience and understanding of employee productivity. (4 marks)",
 4,
 [{"band": "4", "criteria": "Explains how the data visualisations provided could affect the management team's user experience and understanding of employee productivity"},
  {"band": "3", "criteria": "Describes how the data visualisations provided could affect the management team's user experience and understanding of employee productivity"},
  {"band": "2", "criteria": "Outlines how ONE feature of the data visualisations could affect the management team's user experience and/or understanding of employee productivity"},
  {"band": "1", "criteria": "Provides some relevant information"}],
 ["data visualisation", "user experience"],
 ["The data visualisations in the presentation enhance the management team's user experience by making complex employee productivity data easier to understand. Features like clear graphs and charts allow management to quickly identify productivity trends and comparisons across departments, by tailoring the design to highlight key insights through the use of colour and appropriate graph types. The use of the heat map for staff attendance and punctuality patterns creates a real-time, dynamic representation of department staff absences across the company. The continuous updating, clarity and focus of the visualisations improve the team's ability to act on the data effectively and in a timely manner."],
)

# ---------------- Q24 (5 marks, enterprise project) ----------------
add(
 "ec2025-q24",
 "A food company is considering the use of freelance work and offshore development to support its packaging "
 "design.\n\nExplain the advantages and disadvantages to the company in using freelance work and offshore "
 "development for packaging design.",
 5,
 [{"band": "5", "criteria": "Explains advantages and disadvantages to the company in using freelance work and offshore development for packaging design"},
  {"band": "4", "criteria": "Outlines advantages and disadvantages to the company in using freelance work and offshore development for packaging design"},
  {"band": "3", "criteria": "Outlines some features of freelance work and/or offshore development"},
  {"band": "2", "criteria": "Identifies some features of freelance work and/or offshore development"},
  {"band": "1", "criteria": "Provides some relevant information"}],
 ["enterprise project", "changing nature of enterprise"],
 ["Offshore development can provide the company with access to a global talent pool, allowing it to find staff with specialised skills not readily available domestically for technical design work. It also offers significant cost savings, as labour in many regions is less expensive. However, communication barriers such as time zone differences and language challenges can lead to delays and misunderstandings.\nFreelance work offers the company flexibility and the ability to hire experts for short-term or specialised designs. This can reduce overhead costs and improve the efficiency of the company's design workflow. On the other hand, freelancers may not be fully aligned with the company's vision or work processes, which can affect the cohesion of major design projects."],
)

# ---------------- Q25 (8 marks, intelligent systems) ----------------
add(
 "ec2025-q25",
 "View the slideshow about applications of decision support systems.\n"
 "[Note: the slideshow is exam stimulus material (including DSS application examples such as finance/healthcare), visible in the official online exam: https://fam.hsconline.nesa.nsw.edu.au/]\n\n"
 "Explain how intelligent systems can assist the different categories of decision-making. Support your answer "
 "with some examples from the stimulus.",
 8,
 [{"band": "8", "criteria": "Explains how intelligent systems can assist the different categories of decision-making; Supports answer with relevant examples from the stimulus"},
  {"band": "6–7", "criteria": "Describes how intelligent systems can assist the different categories of decision-making in enterprises; Supports answer with some examples from the stimulus"},
  {"band": "4–5", "criteria": "Shows an understanding of how intelligent systems can assist in decision-making; Refers to one or more of the examples in the stimulus"},
  {"band": "2–3", "criteria": "Identifies features of decision support systems and/or intelligent systems"},
  {"band": "1", "criteria": "Provides some relevant information"}],
 ["intelligent systems", "decision support systems", "categories of decision-making"],
 ["Intelligent systems enhance decision-making — structured, semi-structured and unstructured — by increasing speed and accuracy within enterprise systems. In finance, structured decision-making like loan approvals benefit from decision support systems (DSS) that apply predetermined rules to assess credit score, employment history and income. For example, a bank's loan evaluation DSS can instantly approve or reject applications based on set criteria, while streamlining the process.\nSemi-structured decisions require both automated analysis and human judgment. In financial fraud detection, intelligent systems analyse transaction patterns using machine learning algorithms to flag anomalies such as unusual purchase locations or transactions. Fraud detection DSS provide suspicious activity data to analysts to make the final call. This system enables staff to prioritise cases based on risk levels and patterns identified by the software, improving both response time and detection accuracy.\nUnstructured decision-making relies on expert judgment and lacks a fixed process. In healthcare, unstructured decision-making assists doctors in diagnosing rare or complex conditions by analysing patient history, genetic data and clinical trials. Using machine learning and other AI, these systems suggest possible diagnoses or treatments based on related cases and datasets. While the final decision remains with the doctor, the system enhances clinical insight and supports informed judgement."],
)

out = {"subject": "Enterprise Computing", "source": SRC, "questions": Q}
os.makedirs('/home/gaogao/workspace/ai-coach/data', exist_ok=True)
path = '/home/gaogao/workspace/ai-coach/data/questions.json'
with open(path, 'w', encoding='utf-8') as f:
    json.dump(out, f, ensure_ascii=False, indent=2)
print("WROTE", path, "| questions:", len(Q), "| total marks:", sum(q['marks'] for q in Q))
