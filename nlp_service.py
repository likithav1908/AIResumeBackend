import re
from typing import List, Dict

class NLPService:
    def __init__(self):
        # Using fallback NLP without spaCy due to compilation issues
        self.fallback_mode = True
        print("NLP Service initialized in fallback mode (regex-based)")
    
    def load_model(self):
        """Load spaCy model - disabled due to compilation issues"""
        pass
    
    def extract_skills_and_keywords(self, text: str) -> Dict:
        """Extract skills and keywords using regex patterns"""
        if not text:
            return {
                "PERSON": [],
                "ORG": [],
                "SKILL": [],
                "KEYWORDS": [],
                "note": "Using fallback regex extraction"
            }
        
        # Extract entities using regex
        entities = {
            "PERSON": self._extract_persons(text),
            "ORG": self._extract_organizations(text),
            "SKILL": self._extract_skills(text),
            "KEYWORDS": self._extract_keywords(text)
        }
        
        return entities
    
    def _extract_persons(self, text: str) -> List[str]:
        """Extract person names using simple patterns"""
        # Simple person name patterns
        person_patterns = [
            r'\b([A-Z][a-z]+ [A-Z][a-z]+)\b',  # First Last
            r'\b([A-Z]\. [A-Z][a-z]+)\b',     # J. Smith
        ]
        
        persons = []
        for pattern in person_patterns:
            matches = re.findall(pattern, text)
            persons.extend(matches)
        
        # Filter out common non-person matches
        common_words = {'Python', 'Java', 'JavaScript', 'AWS', 'Docker', 'Kubernetes', 'Git', 'Linux', 'HTML', 'CSS', 'Angular', 'Vue', 'MongoDB', 'PostgreSQL', 'MySQL', 'Redis', 'API', 'DevOps', 'CI', 'CD', 'Terraform', 'Ansible', 'Jenkins', 'Azure', 'GCP', 'Firebase', 'Machine', 'Learning', 'AI', 'Data', 'Science', 'TensorFlow', 'PyTorch', 'Keras', 'pandas', 'numpy', 'scikit', 'Apache', 'Nginx', 'Microservices', 'Agile', 'Scrum', 'Jira', 'Confluence', 'Slack'}
        
        return [person for person in persons if person not in common_words][:10]
    
    def _extract_organizations(self, text: str) -> List[str]:
        """Extract organization names"""
        # Common tech companies and organizations
        tech_orgs = [
            'Google', 'Microsoft', 'Apple', 'Amazon', 'Facebook', 'Meta', 'Netflix',
            'Tesla', 'Uber', 'Lyft', 'Airbnb', 'Spotify', 'Twitter', 'LinkedIn',
            'GitHub', 'GitLab', 'Atlassian', 'Salesforce', 'Oracle', 'IBM', 'Intel',
            'Adobe', 'Cisco', 'VMware', 'Dell', 'HP', 'IBM', 'Red Hat'
        ]
        
        found_orgs = []
        for org in tech_orgs:
            if org.lower() in text.lower():
                found_orgs.append(org)
        
        return found_orgs[:10]
    
    def _extract_skills(self, text: str) -> List[str]:
        """Extract technical skills using regex patterns"""
        skill_patterns = [
            # Programming & Tech
            r'\b(Python|Java|JavaScript|React|Node\.js|SQL|AWS|Docker|Kubernetes|Git|Linux|HTML|CSS|Angular|Vue\.js|MongoDB|PostgreSQL|MySQL|Redis|Elasticsearch|GraphQL|REST|API|DevOps|CI\/CD|Terraform|Ansible|Jenkins|Azure|GCP|Firebase|Machine Learning|AI|Data Science|TensorFlow|PyTorch|Keras|pandas|numpy|scikit-learn|Apache|Nginx|Microservices|Agile|Scrum|Jira|Confluence|Slack)\b',
            r'\b(C\+\+|C#|\.NET|PHP|Ruby|Rails|Django|Flask|Spring|Laravel|Symfony|Express|FastAPI|Next\.js|TypeScript|Swift|Kotlin|Rust|Go|Scala|MATLAB|SAS|SPSS|Excel|VBA|PowerShell|Bash|Shell)\b',
            # Business & Commerce Skills
            r'\b(Tally|ERP|SAP|Oracle|QuickBooks|Zoho|FreshBooks|Wave|Xero|Accounting|Bookkeeping|Financial Reporting|GST|Taxation|Auditing|Budgeting|Forecasting|Cost Accounting|Management Accounting|Corporate Finance|Investment Analysis|Risk Management|Compliance|Payroll|Invoicing|Receivables|Payables|General Ledger|Balance Sheet|Income Statement|Cash Flow|Financial Analysis|Business Analysis|Data Analysis|PowerPoint|MS Office|Word|Outlook|Teams|Communication|Presentation|Negotiation|Customer Service|Sales|Marketing|HR|Recruitment|Training|Operations|Logistics|Supply Chain|Inventory|Procurement|Contract Management|Vendor Management|Project Management|Quality Assurance|Documentation|Reporting|Dashboard|KPI|Metrics|Analytics|Research|Planning|Strategy|Leadership|Team Management|Time Management|Problem Solving|Decision Making|Critical Thinking|Analytical Skills|Attention to Detail|Multitasking|Organizational Skills|Interpersonal Skills|Client Relationship|Stakeholder Management|Business Development|Partnership|Networking|Event Management|Travel Coordination|Administrative Support|Office Management|Record Keeping|Filing|Documentation|Correspondence|Email Management|Calendar Management|Meeting Coordination|Travel Booking|Expense Management|Reconciliation|Bank Reconciliation|Tax Returns|GST Returns|TDS|Provident Fund|ESI|Professional Tax|Service Tax|VAT|CST|Excise|Customs|Foreign Trade|Import|Export|Foreign Exchange|Treasury|Cash Management|Working Capital|Capital Budgeting|Investment Appraisal|Cost Benefit Analysis|Break Even Analysis|Ratio Analysis|Fund Flow|Cash Flow|Budgetary Control|Standard Costing|Variance Analysis|Marginal Costing|Activity Based Costing|Lean Manufacturing|Six Sigma|Kaizen|5S|ISO|Quality Control|Process Improvement|Change Management|Business Process Reengineering|Digital Transformation|Automation|Artificial Intelligence|Blockchain|Cloud Computing|Cybersecurity|Data Privacy|GDPR|ITIL|COBIT|Sarbanes Oxley|Internal Audit|External Audit|Statutory Audit|Management Audit|Concurrent Audit|Risk Based Audit|Fraud Detection|Forensic Accounting|Litigation Support|Expert Testimony|Valuation|Mergers|Acquisitions|Due Diligence|Corporate Restructuring|Insolvency|Bankruptcy|Liquidation|Wind Up|Strike Off|Dissolution|Succession Planning|Estate Planning|Trust|Foundation|NGO|Society|Partnership|LLP|Proprietorship|Company Law|FEMA|RBI|SEBI|IRDA|PFRDA|EPFO|ESIC|Labour Laws|Industrial Relations|Collective Bargaining|Trade Union|Grievance Handling|Disciplinary Action|Performance Management|Appraisal|KRA|KPI|OKR|SMART Goals|MBO|360 Degree Feedback|Training Needs Analysis|Skill Gap Analysis|Competency Mapping|Career Planning|Succession Planning|Talent Management|Employee Engagement|Motivation|Retention|Attrition|Exit Interview|Onboarding|Induction|Orientation|Mentoring|Coaching|Counseling|Leadership Development|Management Development|Executive Development|Team Building|Outbound Training|Adventure Learning|Simulation|Role Play|Case Study|Action Learning|Project Based Learning|Experiential Learning|Blended Learning|E Learning|Mobile Learning|Gamification|Micro Learning|Nano Learning|Social Learning|Collaborative Learning|Informal Learning|On the Job Training|Job Rotation|Job Enrichment|Job Enlargement|Job Design|Work Design|Organization Design|Structure Design|Process Design|System Design|Network Design|Service Design|Design Thinking|Innovation Management|Creativity|Ideation|Brainstorming|Mind Mapping|TRIZ|Six Thinking Hats|Lateral Thinking|Vertical Thinking|Critical Thinking|Analytical Thinking|Strategic Thinking|Systems Thinking|Design Thinking|Lean Thinking|Agile Thinking|Digital Thinking|Growth Mindset|Learning Organization|Knowledge Management|Intellectual Capital|Human Capital|Social Capital|Emotional Intelligence|Social Intelligence|Cultural Intelligence|Spiritual Intelligence|Adversity Quotient|Resilience|Stress Management|Work Life Balance|Mindfulness|Meditation|Yoga|Fitness|Wellness|Health|Safety|Environment|Sustainability|CSR|ESG|Triple Bottom Line|Shared Value|Creating Shared Value|Blended Value|Social Impact|Impact Investing|Social Enterprise|NGO|Non Profit|Foundation|Trust|Society|Cooperative|Self Help Group|Microfinance|Microcredit|Microenterprise|Livelihood|Entrepreneurship|Startup|Incubator|Accelerator|Venture Capital|Private Equity|Angel Investor|Crowdfunding|Peer to Peer Lending|Fintech|Insurtech|Healthtech|Edutech|Agritech|Cleantech|Biotech|Medtech|Foodtech|Fashiontech|Sportstech|Traveltech|Realestate|PropTech|ConTech|LegalTech|RegTech|SupTech|GovTech|CivicTech|HealthTech|Digital Health|Telemedicine|E Health|M Health|Wearable|IoT|AI|ML|Blockchain|Cloud|Big Data|Analytics|Data Science|Data Engineering|Data Visualization|Data Governance|Data Quality|Data Security|Data Privacy|Data Ethics|Data Literacy|Data Culture|Data Driven|Evidence Based|Research|Development|Innovation|Patents|Trademarks|Copyrights|Intellectual Property|Technology Transfer|Commercialization|Licensing|Franchising|Joint Venture|Strategic Alliance|Partnership|Collaboration|Coopetition|Networking|Referrals|Word of Mouth|Viral Marketing|Guerilla Marketing|Ambush Marketing|Experiential Marketing|Event Marketing|Sponsorship|Product Placement|Celebrity Endorsement|Influencer Marketing|Affiliate Marketing|Multi Level Marketing|Network Marketing|Direct Selling|E Commerce|M Commerce|Social Commerce|Mobile Commerce|Omni Channel|Phygital|Digital|Online|Internet|Web|Mobile|App|Software|Hardware|Infrastructure|Platform|Ecosystem|Marketplace|Aggregator|Uber|Airbnb|Amazon|Flipkart|Alibaba|eBay|Etsy|Shopify|WooCommerce|Magento|BigCommerce|Salesforce|HubSpot|Marketo|Mailchimp|Constant Contact|AWeber|GetResponse|ConvertKit|ActiveCampaign|Infusionsoft|Ontraport|ClickFunnels|Leadpages|Unbounce|Instapage|Optimizely|Google Analytics|Adobe Analytics|Mixpanel|Kissmetrics|Hotjar|Crazy Egg|FullStory|UserTesting|UsabilityHub|SurveyMonkey|Typeform|Google Forms|SurveyGizmo|Qualtrics|Medallia|Trustpilot|G2Crowd|Capterra|Software Advice|GetApp|SaaSworthy|SourceForge|Product Hunt|AngelList|Crunchbase|PitchBook|CB Insights|Gartner|Forrester|IDC|Gartner|McKinsey|BCG|Bain|Deloitte|PWC|EY|KPMG|Accenture|Capgemini|IBM|Microsoft|Oracle|SAP|Cisco|Intel|HP|Dell|Apple|Google|Amazon|Facebook|Netflix|Tesla|Uber|Airbnb|Spotify|Twitter|LinkedIn|Instagram|YouTube|TikTok|Snapchat|Pinterest|Reddit|WhatsApp|Telegram|Signal|Zoom|Teams|Slack|Discord|Figma|Sketch|Adobe|Canva|Piktochart|Venngage|Infogram|Tableau|PowerBI|QlikView|Spotfire|Looker|Sisense|Domo|Alteryx|KNIME|RapidMiner|DataRobot|H2Oai|Algorithmia|AWS|Azure|GCP|DigitalOcean|Linode|Vultr|Heroku|Netlify|Vercel|GitHub|GitLab|Bitbucket|Jira|Confluence|Trello|Asana|Monday|ClickUp|Notion|Airtable|Coda|Roam Research|Obsidian|Evernote|OneNote|Google Keep|Bear|Ulysses|Scrivener|Notion++|Typora|IA Writer|Ulysses|Scrivener|Final Draft| Celtx|Fade In|WriterDuet|Highland 2|Slugline|Trelby|Causality|WriterDuet|StudioBinder|Scriptation|Final Draft|Celtx|Fade In|Scrivener|Ulysses|IA Writer|Typora|Bear|Notion|Obsidian|Roam Research|Evernote|OneNote|Google Keep|Apple Notes|Samsung Notes|OneNote|Google Keep|Apple Notes|Samsung Notes)\b'
        ]
        
        skills = set()
        for pattern in skill_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            skills.update(matches)
        
        return list(skills)
    
    def _extract_keywords(self, text: str) -> List[str]:
        """Extract important keywords from text"""
        # Common technical and business keywords
        keyword_patterns = [
            r'\b(software|development|engineering|architecture|design|testing|deployment|integration|optimization|performance|scalability|security|monitoring|automation|analytics|reporting|dashboard|frontend|backend|fullstack|mobile|web|cloud|infrastructure|database|network|system|application|service|platform|solution|product|project|team|management|leadership|communication|collaboration|innovation|strategy|planning|execution|delivery|quality|maintenance|support|troubleshooting|documentation|research|analysis|implementation|configuration|installation|migration|backup|recovery|compliance|audit|review|assessment|consulting|training|mentoring|coaching)\b',
            # Commerce & Finance keywords
            r'\b(accounting|finance|financial|commerce|business|corporate|commercial|industrial|professional|executive|administrative|clerical|support|operations|management|marketing|sales|customer|client|service|relationship|partnership|vendor|supplier|procurement|purchasing|inventory|stock|warehouse|logistics|supply|chain|distribution|retail|wholesale|trade|import|export|customs|excise|gst|vat|tax|income|corporate|deduction|exemption|refund|return|filing|compliance|regulatory|statutory|legal|contract|agreement|terms|conditions|policy|procedure|guideline|standard|norm|benchmark|best|practice|framework|methodology|process|workflow|system|control|audit|review|verification|validation|authorization|approval|sign|off|check|balance|reconcile|match|adjust|correct|rectify|amend|update|modify|change|revise|improve|enhance|optimize|streamline|simplify|automate|digitize|transform|modernize|upgrade|migrate|convert|integrate|interface|connect|link|bridge|gateway|portal|hub|center|node|point|access|entry|exit|input|output|flow|stream|path|route|channel|medium|mode|format|structure|layout|design|template|form|document|record|file|folder|directory|database|table|field|column|row|cell|value|data|information|content|text|number|figure|chart|graph|report|summary|detail|overview|snapshot|status|progress|update|notification|alert|message|email|letter|memo|note|comment|remark|observation|finding|result|conclusion|recommendation|suggestion|proposal|plan|schedule|timeline|deadline|milestone|deliverable|output|outcome|benefit|advantage|feature|characteristic|attribute|property|quality|specification|requirement|criterion|metric|parameter|variable|factor|element|component|part|section|segment|portion|piece|item|unit|entity|object|instance|occurrence|event|activity|task|job|function|role|responsibility|duty|obligation|commitment|promise|guarantee|warranty|assurance|confidence|trust|faith|belief|hope|expectation|anticipation|prediction|forecast|projection|estimate|approximation|calculation|computation|analysis|evaluation|assessment|judgment|decision|choice|selection|option|alternative|possibility|opportunity|potential|prospect|future|tomorrow|today|now|current|present|past|previous|former|later|next|following|subsequent|consequent|resultant|final|ultimate|last|ending|closing|concluding|finishing|completing|terminating|ending|stopping|ceasing|halting|pausing|waiting|delaying|postponing|rescheduling|cancelling|dropping|removing|deleting|erasing|destroying|damaging|breaking|repairing|fixing|solving|resolving|addressing|handling|managing|dealing|coping|facing|confronting|meeting|encountering|experiencing|undergoing|suffering|enduring|bearing|tolerating|accepting|rejecting|refusing|denying|disagreeing|objecting|protesting|complaining|criticizing|blaming|accusing|charging|suing|prosecuting|defending|protecting|guarding|shielding|covering|hiding|concealing|revealing|disclosing|sharing|distributing|spreading|circulating|broadcasting|publishing|announcing|declaring|stating|saying|speaking|talking|communicating|expressing|conveying|transmitting|sending|receiving|getting|obtaining|acquiring|gaining|earning|winning|losing|failing|succeeding|achieving|accomplishing|completing|finishing|ending|closing|stopping|quitting|resigning|retiring|leaving|departing|going|moving|traveling|journeying|visiting|touring|exploring|discovering|finding|locating|searching|looking|seeking|hunting|chasing|pursuing|following|tracking|tracing|monitoring|watching|observing|seeing|viewing|looking|staring|gazing|glancing|peeking|glimping|noticing|recognizing|identifying|distinguishing|differentiating|separating|dividing|splitting|breaking|cutting|tearing|ripping|shredding|crushing|destroying|demolishing|wrecking|ruining|damaging|harming|hurting|injuring|wounding|attacking|assaulting|fighting|battling|competing|contesting|opposing|resisting|protesting|objecting|disagreeing|arguing|debating|discussing|negotiating|bargaining|trading|exchanging|swapping|switching|changing|altering|modifying|adjusting|adapting|conforming|fitting|matching|suiting|corresponding|relating|connecting|linking|joining|attaching|fastening|tying|binding|securing|locking|unlocking|opening|closing|shutting|covering|uncovering|revealing|exposing|hiding|concealing|masking|disguising|pretending|acting|performing|playing|entertaining|amusing|interesting|fascinating|exciting|thrilling|frightening|scaring|terrifying|shocking|surprising|amazing|astonishing|stunning|breathtaking|overwhelming|powerful|strong|weak|feeble|fragile|delicate|tough|hard|soft|smooth|rough|coarse|fine|thick|thin|wide|narrow|broad|slim|fat|skinny|large|small|big|little|huge|tiny|giant|miniature|massive|enormous|immense|colossal|gigantic|vast|expansive|spacious|compact|crowded|empty|full|occupied|vacant|available|busy|idle|active|passive|dynamic|static|moving|still|running|walking|standing|sitting|lying|sleeping|resting|working|playing|studying|learning|teaching|training|coaching|mentoring|guiding|leading|following|directing|managing|controlling|supervising|overseeing|monitoring|checking|inspecting|examining|testing|trying|attempting|effort|struggle|fight|battle|war|conflict|dispute|argument|discussion|conversation|dialogue|talk|speech|lecture|presentation|demonstration|exhibition|show|display|performance|concert|event|occasion|ceremony|celebration|party|festival|holiday|vacation|break|rest|pause|stop|end|beginning|start|commencement|initiation|introduction|opening|launch|release|publication|announcement|declaration|statement|proclamation|broadcast|transmission|communication|message|information|data|knowledge|wisdom|intelligence|understanding|comprehension|awareness|consciousness|realization|recognition|acknowledgment|acceptance|approval|agreement|consent|permission|authorization|license|permit|certificate|degree|diploma|qualification|skill|ability|talent|gift|capacity|capability|competence|expertise|mastery|proficiency|specialization|focus|concentration|attention|care|caution|warning|alert|notice|notification|announcement|declaration|statement|proclamation|broadcast|transmission|communication|message|information|data|knowledge|wisdom|intelligence|understanding|comprehension|awareness|consciousness|realization|recognition|acknowledgment|acceptance|approval|agreement|consent|permission|authorization|license|permit|certificate|degree|diploma|qualification|skill|ability|talent|gift|capacity|capability|competence|expertise|mastery|proficiency|specialization)\b'
        ]
        
        keywords = set()
        for pattern in keyword_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            keywords.update(matches)
        
        # Also extract important nouns (simple approach)
        words = re.findall(r'\b[a-zA-Z]{4,}\b', text.lower())
        
        # Filter out common words
        common_words = {'that', 'with', 'have', 'this', 'will', 'your', 'from', 'they', 'know', 'want', 'been', 'good', 'much', 'some', 'time', 'very', 'when', 'come', 'here', 'just', 'like', 'long', 'make', 'many', 'over', 'such', 'take', 'than', 'call', 'who', 'oil', 'sit', 'now', 'find', 'where', 'would', 'first', 'think', 'back', 'hand', 'only', 'tell', 'even', 'most', 'after', 'also', 'well', 'work', 'life', 'only', 'leave', 'year', 'being', 'day', 'same', 'keep', 'last', 'never', 'those', 'feel', 'seem', 'show', 'large', 'often', 'turn', 'real', 'might', 'said', 'say', 'help', 'great', 'little', 'still', 'between', 'old', 'high', 'too', 'place', 'such', 'live', 'back', 'only', 'think', 'hand', 'year', 'good', 'take', 'come', 'know', 'see', 'look', 'want', 'give', 'use', 'find', 'tell', 'ask', 'work', 'seem', 'feel', 'try', 'leave', 'call', 'bring', 'start', 'run', 'show', 'move', 'turn', 'help', 'play', 'hold', 'give', 'face', 'make', 'name', 'time', 'like', 'open', 'seem', 'next', 'stop', 'take', 'come', 'know', 'see', 'look', 'want', 'give', 'use', 'find', 'tell', 'ask', 'work', 'seem', 'feel', 'try', 'leave', 'call', 'bring', 'start', 'run', 'show', 'move', 'turn', 'help', 'play', 'hold', 'give', 'face', 'make', 'name', 'time', 'like', 'open'}
        
        important_words = [word for word in words if word not in common_words and len(word) > 4]
        keywords.update(important_words[:20])  # Add top 20 important words
        
        return list(keywords)
