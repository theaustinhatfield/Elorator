"""Preseed the YC arena with 30 apps (humans + AI models) and run an AI tournament.

Usage:
    python manage.py seed_yc_arena [--reset] [--matches 8]
"""
from django.contrib.auth.models import User
from django.core.management.base import BaseCommand

REAL_APPS = [
    dict(
        source='human',
        model='',
        company='Dropbox',
        tagline='Cloud sync that just works for files',
        pitch="Dropbox synchronizes files across your/your team's computers. It's much better than uploading or email, because it's automatic, integrated into Windows, and fits into the way you already work. There's also a web interface, and the files are securely backed up to Amazon S3. Dropbox is kind of like taking the best elements of subversion, trac and rsync and making them 'just work' for the average individual or team. It's currently in private beta and I add batches of people every few days. Planned freemium: free 1GB, ~$5/mo for 10GB, plus team and enterprise tiers.",
        founders='YC S07 (funded). Drew Houston: programming since age 5, profitable online SAT prep company in college, wrote a real-money poker bot. Leaving Bit9 to work on this full time.',
    ),
    dict(
        source='human',
        model='',
        company='GitLab',
        tagline='Open-source code collaboration, self-hosted',
        pitch="We're making open source software to collaborate on code. It started as 'run your own GitHub' that most users deploy on their own server(s). GitLab allows you to version control code including pull/merge requests, forking and public projects. It also includes project wikis and an issue tracker. Over 100k organizations use it, including Qualcomm, NASA and Nasdaq OMX as paying customers. We also offer GitLab CI that tests code with a distributed set of workers. Traction: $1M ARR run rate, ~1M users, ~60% monthly revenue growth. Declined a $10M acquisition offer.",
        founders='YC W15 (funded). Sytse Sijbrandij + Dmitriy Zaporozhets. 600+ contributors, most popular open source version control software.',
    ),
    dict(
        source='human',
        model='',
        company='Mixpanel',
        tagline='Event analytics, not just pageviews',
        pitch='Mixpanel is a business intelligence service that helps improve online companies by tracking user interactions, engagement, and optimization avenues instead of just tracking page views. It lets teams learn about customers through interaction data and identify conversion funnels — the paths visitors take to registrations, purchases or goal pages. Companies otherwise burn scarce time and money building homebrew internal analytics that are less robust. Alpha already earning revenue at a profit, with Posterous, TicketStumbler and HeyZap integrating. Freemium subscription scaled on usage, like Amazon S3.',
        founders='YC S09 (funded). Suhail Doshi: OpenSocial apps with 1M+ installs. Tim Trefren: top 1% SAT, National Merit Scholar. Both committed full-time.',
    ),
    dict(
        source='human',
        model='',
        company='Cruise',
        tagline='Aftermarket self-driving for existing cars',
        pitch='Cruise builds a system that inexpensively turns your car into a self-driving vehicle. The product is an aftermarket add-on for certain vehicles that bolts on like a roof rack, with cameras, radar, GPS and other sensors, targeting under $3,000 per unit — an order of magnitude cheaper than current efforts. We constrain the problem with commodity hardware and proven algorithms, solving 90% of scenarios. JD Power found 20% of drivers would buy self-driving tech at ~$3k: a $100B+ US market. Revenue from hardware sales/installs, then subscriptions.',
        founders='YC W14 (funded). Kyle Vogt + Jeremy Guillory. Both built self-driving cars before (DARPA challenges, Graymatter, MIT). Demo Audi S4 acquired in first two weeks.',
    ),
    dict(
        source='human',
        model='',
        company='OpenPhone',
        tagline='Phone system meets CRM for small business',
        pitch='OpenPhone is a phone system equipped with CRM capabilities, built from the ground up for small businesses. Through our mobile app, owners get a dedicated business number on existing devices — personalized voicemail, business hours, shared team inboxes, appointment scheduling, docs/signatures/payments over text, and integrations. We own the communication channel, so the CRM fills itself instead of burdening the user. Launched Jan 2018: 1,500 users at 200% MoM, 32 paying at $10/mo within two weeks of launching billing. Subscription $10/mo scaling to $50-200 tiers.',
        founders='YC S18 (funded). Ex-Joist mobile products for 500k+ trade contractors; cofounder launched Vidyard GoVideo to 200k+ users.',
    ),
    dict(
        source='human',
        model='',
        company='Paystack',
        tagline='Stripe for African merchants',
        pitch='Software and services for merchants in Africa to accept online payments from local and international customers. Full-stack APIs that securely collect, encrypt, transmit and store card data in a protected vault, with continuous anti-fraud and chargeback protection. Partnered with Access Bank (3rd largest in Nigeria), PCI-compliant infrastructure built. Private beta: 12 pilot merchants, 400 on the waitlist growing 10x monthly, transaction volume up 15x, $1,300 revenue. Merchants use it even without settlements working yet. Revenue: 1.9% + 50c per transaction.',
        founders='YC W16 (funded). Shola Akinlade: spent 2014 implementing bank payment systems after living this pain since his first startup in 2010. 150+ merchant conversations.',
    ),
    dict(
        source='human',
        model='',
        company='CommandBar',
        tagline='Command bar for any web app (applied as Foobar)',
        pitch='Foobar is a searchbar built into web apps that lets end-users discover and actually execute commands — not just search — straight from the searchbar. A configurable web component a front-end developer can prototype in minutes. Improves onboarding, feature discovery, and retention, plus a web interface for maintaining commands, personalization, and analytics on user intent. 4 apps (Kapwing, StdLib, Plan, Meetingbird) committed to free pilots. Our insight: an executable searchbar should be a bought product, not a built feature — and the intent-to-action maps it creates are a network-effect moat. Subscription ~$100-1000/mo like Intercom.',
        founders='YC S20 (funded). 3 founders; previously built codePost to 60 universities over 12 months full-time before pivoting.',
    ),
    dict(
        source='human',
        model='',
        company='Apptimize',
        tagline='A/B testing for native mobile apps',
        pitch='Apptimize lets you A/B test mobile applications while keeping the native experience — no blind pushes, no waiting on app updates or users to upgrade. Web dashboard plus WYSIWYG editor so non-programmers can run experiments. Removes the pain of designing controlled experiments, serving variations, collecting results, and calculating statistical significance — handling mobile-hard problems (intermittent internet, no cookies, version fragmentation) as its core business. Private beta launched with 100+ signups, end-to-end on Android, iOS coming. Plan: monthly subscriptions, ~$1K/mo premium tier.',
        founders='YC S13 (funded). Nancy Hua: ran Fixed Income Quant Strategies at GETCO. Jeremy: owned IndexedDB in Chrome, started the London Chrome team.',
    ),
]

SEED_APPS = [
    dict(
        source='human',
        model='',
        company='Elorator',
        tagline='LMArena for startup ideas, via MCP',
        pitch='Elorator is a pairwise Elo arena for YC-style startup pitches that AI agents query over MCP and founders use to pre-test applications. Submitters get 10 placement matches against anchored ideas and receive an Elo, percentile, and per-match reasons. Public submissions are free and listed; private ratings are hidden and paid. We launched with 150 anchored AI pitches and charge $29 per private rating plus $99/mo API plans for agent operators running bulk idea search.',
        founders='Solo technical founder, built Elo ranking apps before',
    ),
    dict(
        source='human',
        model='',
        company='VetBill',
        tagline='Stripe for vet clinics',
        pitch='VetBill replaces the paper checkout binder at independent vet clinics with card-on-file billing, estimates over text, and automated payment plans. 3 design-partner clinics in Austin process $41k/mo through us; we take 1.5% + 30c. Clinics lose 6% of revenue to no-shows and unpaid estimates today; our text-to-pay flow recovered $18k in 60 days at the pilot. Next: 20 clinics via the state vet association reseller deal.',
        founders='Ex-Square payments engineer + vet tech cofounder',
    ),
    dict(
        source='human',
        model='',
        company='RFI Copilot',
        tagline='Submittal triage for GCs',
        pitch='RFI Copilot reads spec PDFs and auto-drafts RFI responses for mid-size general contractors, cutting turnaround from 6 days to same-day. Two GCs pay $1,200/mo each after a 30-day pilot covering 214 RFIs with 92% accepted without edits. We integrate with Procore and Autodesk. Construction admin is a $12B market and RFI delays cause $30k/day in standby costs on commercial jobs.',
        founders='2 ex-Procore engineers',
    ),
    dict(
        source='human',
        model='',
        company='SmileFill',
        tagline='Backfill cancelled dental appointments',
        pitch='SmileFill texts waitlisted patients the moment a dental slot cancels and fills it in under 4 minutes on average. Our 5-clinic pilot filled 312 appointments worth $96k in production in 90 days at $249/clinic/mo. Dental no-shows cost US practices $3B/yr. We integrate with Dentrix and Eaglesoft in one click.',
        founders='Dental office manager turned founder + engineer brother',
    ),
    dict(
        source='human',
        model='',
        company='DripWatch',
        tagline='Leak alerts for drip irrigation',
        pitch='DripWatch clamps $39 acoustic sensors onto drip lines and texts almond growers when a line bursts, saving ~400k gallons per incident. 11 farms paid $2,900 each for the season; 2 renewed for 3 years. California groundwater rules now fine over-pumpers $500/acre-foot, so payback is under one season.',
        founders='Ag irrigation consultant + embedded engineer',
    ),
    dict(
        source='human',
        model='',
        company='Block dues',
        tagline='HOA dues without the drama',
        pitch='Block dues gives self-managed HOAs a simple ledger, autopay, and late-fee enforcement for $49/mo per association. 40 HOAs onboarded via property-management accountants; $1,960 MRR, 4% monthly churn. 350k US HOAs still run on spreadsheets and shoeboxes.',
        founders='CPA who managed 12 HOAs',
    ),
    dict(
        source='human',
        model='',
        company='DetentionPay',
        tagline='Detention billing for small fleets',
        pitch='DetentionPay pulls ELD timestamps and auto-invoices brokers for driver detention at $75/hr. 22 owner-operators recovered an average $1,140 each last quarter; we take 8%. Small fleets lose 12% of revenue to unpaid detention because billing takes hours they do not have.',
        founders='Ex-trucker dispatcher + daughter engineer',
    ),
    dict(
        source='human',
        model='',
        company='PewKeep',
        tagline='Churn alerts for churches',
        pitch='PewKeep flags lapsed givers from church ChMS data and drafts pastoral follow-ups, recovering an average $8,400/yr per congregation in our 14-church pilot at $99/mo. US churches lose 20% of givers yearly to silent drift.',
        founders='Former church admin, self-taught dev',
    ),
    dict(
        source='human',
        model='',
        company='Waggo',
        tagline='Uber for dog walking, revolutionized',
        pitch='Waggo will revolutionize pet care with an AI-powered platform that unlocks the power of community to deliver game-changing experiences for dogs everywhere. Our paradigm shift will disrupt everything about walking.',
        founders='',
    ),
    dict(
        source='human',
        model='',
        company='SynergizeAI',
        tagline='AI-powered platform for synergy',
        pitch='SynergizeAI is a world-changing AI-powered platform to unlock the power of teams through revolutionary game-changing workflows that disrupt everything. Backed by vibes.',
        founders='',
    ),
    dict(
        source='human',
        model='',
        company='QuoteMill',
        tagline='Instant quotes for machine shops',
        pitch='QuoteMill turns STEP files into priced quotes in 90 seconds for job shops, vs 3 days manually. 6 shops pay $600/mo; quote volume up 3x, win rate flat. Job shops lose $200B in RFQs yearly to slow response. We integrate with JobBOSS.',
        founders='Machinist + ML engineer',
    ),
    dict(
        source='human',
        model='',
        company='PrepLess',
        tagline='Prep lists from POS history for restaurants',
        pitch='PrepLess converts 8 weeks of POS sales into daily prep sheets, cutting food waste 18% across 9 restaurants at $129/mo each. Restaurants throw away 4-10% of food purchased; labor for manual prep counts takes 45 min/day.',
        founders='Ex-line cook, now dev',
    ),
    dict(
        source='ai',
        model='chatgpt',
        company='EvidenceBin',
        tagline='SOC 2 audit evidence that collects itself',
        pitch='The problem: every startup selling to businesses eventually gets asked for SOC 2 compliance, and preparing for the audit eats weeks of founder and engineering time spent taking screenshots of settings pages and chasing access reviews. EvidenceBin connects to the tools a startup already uses — Google Workspace, AWS, GitHub — and continuously gathers the proof auditors ask for: who has access to what, what changed, and when. When audit season comes, the company exports one organized packet instead of scrambling. Customers would be seed-stage B2B startups facing their first enterprise security review, paying a monthly subscription. The timing works because almost every mid-market buyer now requires SOC 2 before signing, so demand is forced rather than optional. The biggest risk is the established compliance platforms, which could add the same automatic collection to products customers already pay for.',
        founders='AI-generated seed idea',
    ),
    dict(
        source='ai',
        model='chatgpt',
        company='LabSign',
        tagline='E-signature built for medical lab paperwork',
        pitch='The problem: independent medical labs still run on fax machines because generic e-signature tools cannot handle lab-specific paperwork like requisition forms tied to a doctor order and insurance pre-authorization. LabSign is an e-signature product shaped around that workflow: the requisition, the patient consent, and the payer authorization travel together as one packet instead of three separate faxes. Customers would be independent and regional labs, charged per envelope sent. The timing works because insurers keep tightening prior-authorization rules, so the paperwork burden grows every year whether labs like it or not. The biggest risk is market size — selling into small labs one by one is slow, and the largest lab chains build this themselves.',
        founders='AI-generated seed idea',
    ),
    dict(
        source='ai',
        model='chatgpt',
        company='MoonTasks',
        tagline='A to-do list app',
        pitch='The problem, as far as this pitch goes, is that people have a lot to do and sometimes forget things. MoonTasks would be a mobile app where you write down tasks, organize them into lists, and get reminders when they are due. It would look clean and be easy to use. There is no particular customer in mind beyond anyone who has tasks, no explanation of why existing reminders and notes apps fall short, and no clear plan for making money beyond possibly charging for extra features someday. There is also no reason why this needs to exist now rather than at any point in the last fifteen years. The biggest risk is that this describes hundreds of existing apps with no reason for anyone to switch.',
        founders='AI-generated seed idea',
    ),
    dict(
        source='ai',
        model='chatgpt',
        company='LeaseLens',
        tagline='Catches overcharges buried in retail leases',
        pitch='The problem: retail chains leasing dozens of storefronts pay triple-net leases where the landlord passes through shared maintenance costs, and those passed-through charges are full of errors that tenants never check because the paperwork is dense and boring. LeaseLens audits those charges line by line against what the lease actually allows, then handles the dispute letters to recover the difference. Customers would be regional retail chains, paying either a share of whatever is recovered or a yearly monitoring fee per store. The timing works because retail margins keep thinning, so finance teams are hunting for found money inside costs they already pay. The biggest risk is that the revenue is lumpy and service-heavy — every recovery is a custom fight, which is hard to turn into smooth recurring software income.',
        founders='AI-generated seed idea',
    ),
    dict(
        source='ai',
        model='chatgpt',
        company='RecallDesk',
        tagline='Turns open car recalls into booked repair jobs',
        pitch='The problem: tens of millions of cars on the road have open safety recalls, and independent repair shops do nothing about it because checking every customer car against the recall database by hand is tedious. RecallDesk does that matching automatically every night from the plate numbers already in the shop system, then drafts the text messages inviting owners in for the free recall fix — which usually turns into paid work when the car is already on the lift. Customers would be independent auto shops paying a monthly subscription. The timing works because recall volumes keep growing while shops compete harder for every service visit. The biggest risk is apathy: the shops that ignore recalls today may also ignore a tool that reminds them about recalls.',
        founders='AI-generated seed idea',
    ),
    dict(
        source='ai',
        model='claude',
        company='PriorAuth Pilot',
        tagline='Insurance approval paperwork for physical therapy clinics',
        pitch='The problem: physical therapy clinics lose a meaningful share of revenue when insurers deny claims over prior-authorization paperwork mistakes, and the front desk staff appealing those denials are already overwhelmed. PriorAuth Pilot assembles each authorization packet the way the specific payer wants it — the right forms, the right clinical notes attached, the right codes — before it is submitted, instead of after it gets rejected. Customers would be PT clinics paying a monthly subscription, and the product would plug into the practice software they already use. The timing works because payers keep adding authorization requirements while clinics cannot hire more admin staff. The biggest risk is maintenance: every payer changes its rules constantly, so the product is only as good as its rulebook, which must be updated forever.',
        founders='AI-generated seed idea',
    ),
    dict(
        source='ai',
        model='claude',
        company='SdsSnap',
        tagline='Workplace chemical-safety binders from phone photos',
        pitch='The problem: contractors and small manufacturers are legally required to keep safety data sheets for every chemical on site, and the standard solution is a dusty paper binder that is out of date and fails inspections. SdsSnap lets a foreman photograph a product label with a phone and get back a compliant digital binder page with a QR code posted on the shop floor, so the binder maintains itself as products change. Customers would be small contractors and workshops paying a modest yearly fee per site. The timing works because safety fines keep rising while every foreman already carries a good camera. The biggest risk is that demand is episodic — customers care intensely the month before an inspection and forget the product exists the rest of the year.',
        founders='AI-generated seed idea',
    ),
    dict(
        source='ai',
        model='claude',
        company='NebulaHire',
        tagline='AI matching for job applicants',
        pitch='The problem, loosely stated, is that hiring takes a long time and reviewing resumes is boring. NebulaHire would use AI to match candidates with jobs automatically, saving everyone time. The pitch never specifies who the customer is — employers, recruiters, or job seekers — or what exactly the AI looks at beyond resumes, or why its matches would beat a keyword search. Making money is described vaguely as charging companies somehow. There is no reason this moment is special for the idea, and no acknowledgment that every applicant tracking system already advertises the same AI matching. The biggest risk is that without a specific wedge or proprietary data, this is a feature description competing against incumbents who already own the customer relationship.',
        founders='AI-generated seed idea',
    ),
    dict(
        source='ai',
        model='claude',
        company='ColdSnap',
        tagline='Fridge-failure alarms for independent grocers',
        pitch='The problem: when a walk-in freezer dies overnight, an independent grocer can lose a whole inventory of spoiled food by morning, and the monitoring systems that prevent this cost thousands to install, so small stores simply go without. ColdSnap is a small battery sensor that sticks to the freezer wall in minutes and texts the manager the moment temperatures drift, long before food is ruined. Customers would be independent grocery and convenience stores paying a small monthly fee per sensor. The timing works because sensors and cellular parts have become cheap enough to sell protection for the price of a sandwich per month. The biggest risk is hardware itself — shipping devices, replacing batteries, and supporting non-technical owners store by store is a grind with thin margins.',
        founders='AI-generated seed idea',
    ),
    dict(
        source='ai',
        model='claude',
        company='PermitPath',
        tagline='Building-permit packets for backyard-home builders',
        pitch='The problem: builders putting up backyard homes in California wait many months for permits largely because each city wants the paperwork in a slightly different format, so applications bounce back for resubmittal again and again. PermitPath produces the full packet shaped to the specific jurisdiction — the right forms, the right plan annotations, the common gotchas pre-checked — before the first submission. Customers would be small builders and homeowners managing their own builds, paying a flat fee per project. The timing works because state laws recently made backyard homes far easier to approve, creating a wave of first-time builders hitting this paperwork wall. The biggest risk is that the product chases moving rules across hundreds of cities, and demand rises and falls with housing cycles outside its control.',
        founders='AI-generated seed idea',
    ),
    dict(
        source='ai',
        model='muse-spark-1.3',
        company='JudgeLens',
        tagline='Small-claims paperwork for independent landlords',
        pitch='The problem: independent landlords regularly get stiffed on amounts too small to justify hiring a lawyer — a skipped cleaning bill, a broken blind, a few hundred in unpaid rent — so they just absorb the loss. JudgeLens turns the lease and payment history into a finished demand letter and, if that fails, a ready-to-file small-claims packet for the local court. Customers would be mom-and-pop landlords paying a flat fee per case, which is a fraction of even one hour of legal help. The timing works because courts have moved more of this process online, lowering the barrier for self-filers. The biggest risk is retention: a customer who wins their case has no reason to come back until the next bad tenant, which might be years away.',
        founders='AI-generated seed idea',
    ),
    dict(
        source='ai',
        model='muse-spark-1.3',
        company='RouteRescue',
        tagline='Refunds for missed garbage pickups, claimed automatically',
        pitch='The problem: haulers miss scheduled pickups at apartment buildings all the time, and property managers eat the cost because proving each miss and filing for the service credit takes more staff time than the credit is worth. RouteRescue watches the hauler location data and tenant complaints, identifies the missed stops, and files the credit claims with the hauler on the manager behalf. Customers would be property managers paying a small monthly fee per unit, positioned as found money against a bill they already pay. The timing works because haulers now expose enough tracking data to make the misses provable. The biggest risk is dependence on that data — if haulers restrict access the moment claims start costing them real money, the product goes blind.',
        founders='AI-generated seed idea',
    ),
    dict(
        source='ai',
        model='muse-spark-1.3',
        company='VibeFlow',
        tagline='Dashboard measuring team focus',
        pitch='The problem, as presented, is that remote teams might not be focused, and managers cannot tell. VibeFlow would be a dashboard showing each team focus score computed from their work apps. The pitch never says what a focus score is made of, what a manager is supposed to do differently on seeing it, or why any team would agree to be measured this way. The customer is vaguely teams, the price is undecided, and the reason to build it now is that remote work exists. The biggest risk is everything upstream of revenue: employee surveillance tools face cultural resistance, the metric has no demonstrated link to output, and selling monitoring to managers while imposing it on workers means the buyer and the user want opposite things.',
        founders='AI-generated seed idea',
    ),
    dict(
        source='ai',
        model='muse-spark-1.3',
        company='TipAudit',
        tagline='Tip-pool rule checks for restaurant groups',
        pitch='The problem: tip-pooling rules changed recently, and restaurant groups with many locations cannot tell from their point-of-sale reports alone whether each store split tips legally — until a labor lawyer or a lawsuit tells them. TipAudit reconciles tip records against the current rules every week and flags the violations while they are still fixable. Customers would be multi-location restaurant groups paying a monthly subscription, sold as insurance against the kind of settlement that dwarfs years of fees. The timing works because the rule change is recent, so most groups are non-compliant without knowing it. The biggest risk is that the best outcome for the customer — becoming compliant — removes the urgency to keep paying, and the niche only spans as far as the regulation reaches.',
        founders='AI-generated seed idea',
    ),
    dict(
        source='ai',
        model='glm-5.3',
        company='MedStock',
        tagline='Expiry tracking for emergency medications',
        pitch='The problem: surgery centers keep crash carts stocked with emergency drugs, and when surveyors find an expired vial the citation is serious — yet tracking expiry dates across carts, closets, and fridges is a clipboard chore that slips. MedStock lets a nurse photograph the cart once a month and flags everything expiring soon, with a clear restock list per location. Customers would be outpatient surgery centers and clinics paying a monthly subscription per facility. The timing works because accreditation scrutiny keeps tightening while staffing stays thin, so automated checks replace work nobody has time for. The biggest risk is the sales cycle: clinical buyers move slowly, and each facility needs its own onboarding before the subscription means anything.',
        founders='AI-generated seed idea',
    ),
    dict(
        source='ai',
        model='glm-5.3',
        company='SubMeter',
        tagline='Fair utility splitting for shared-meter buildings',
        pitch='The problem: in buildings with one master utility meter, landlords split the bill by rough rules of thumb, so some tenants quietly overpay for years while others underpay — and every split spawns disputes. SubMeter computes each unit share from square footage, occupancy, and major appliances, producing a bill tenants can actually understand and a paper trail for arguments. Customers would be small landlords and building managers paying a small monthly fee per unit. The timing works because utility prices keep climbing, which turns background grumbling about fairness into active fights worth paying to resolve. The biggest risk is apathy on both sides: landlords who benefit from the status quo will not buy, and edge cases like sublets and vacant units threaten the feeling of fairness the whole product rests on.',
        founders='AI-generated seed idea',
    ),
    dict(
        source='ai',
        model='glm-5.3',
        company='OmniVerse',
        tagline='One app to replace all business software',
        pitch='The problem, as presented, is that businesses use too many different software tools. OmniVerse would be a single platform that does everything those tools do — messaging, documents, accounting, customer management, and more — in one place. The pitch never identifies a first customer, a first workflow to nail, or a reason any team would migrate off tools that already work. Making money is assumed to follow from having all the users, and the timing argument is that technology has advanced. The biggest risk is the strategy itself: every successful platform started with one beloved use case, while everything-for-everyone from day one means competing with every incumbent simultaneously with no wedge and no switching incentive.',
        founders='AI-generated seed idea',
    ),
    dict(
        source='ai',
        model='glm-5.3',
        company='WarrantyWin',
        tagline='Unclaimed equipment warranties for school districts',
        pitch='The problem: school districts own enormous fleets of heating, cooling, and kitchen equipment, each piece carrying a manufacturer warranty — and the records live in filing cabinets, so warranties quietly expire unused while districts pay for repairs out of pocket. WarrantyWin builds the asset register from purchase records, tracks every warranty end date, and files the claim paperwork before expiry. Customers would be school districts paying a yearly subscription, positioned against repair budgets that dwarf the fee. The timing works because maintenance backlogs keep growing while district budgets do not, making found money attractive. The biggest risk is procurement: selling to districts means slow approvals, pilot committees, and budget cycles, so a great product can still take years per customer.',
        founders='AI-generated seed idea',
    ),
]


class Command(BaseCommand):
    help = 'Preseed YC arena with 30 apps + run AI tournament.'

    def add_arguments(self, parser):
        parser.add_argument('--reset', action='store_true',
                            help='Delete existing arena submissions first')
        parser.add_argument('--matches', type=int, default=8,
                            help='Matches per entry in tournament')
        parser.add_argument('--round-robin', action='store_true',
                            help='Every pair meets exactly once (max info for a deterministic judge)')

    def handle(self, *args, **opts):
        from core.models import Contest, EloRating, Submission
        from core.views import ARENA_DESCRIPTION, ARENA_TITLE
        from core.services import run_full_round_robin, run_tournament

        arena, _ = Contest.objects.get_or_create(
            title=ARENA_TITLE,
            defaults={'description': ARENA_DESCRIPTION, 'creator': self._get_creator()},
        )
        if opts['reset']:
            arena.submissions.all().delete()
            arena.matches.all().delete()

        existing = set(arena.submissions.values_list('company_name', flat=True))
        created = 0
        # AI entries from SEED_APPS + real funded humans from REAL_APPS.
        apps = [a for a in SEED_APPS if a['source'] != 'human'] + REAL_APPS
        for app in apps:
            if app['company'] in existing:
                continue
            sub = Submission.objects.create(
                contest=arena,
                submitter=None,
                name=app['company'][:255],
                description=app['pitch'][:2000],
                company_name=app['company'][:255],
                tagline=app.get('tagline', '')[:140],
                pitch=app['pitch'],
                founders_blurb=app.get('founders', '')[:500],
                source=app['source'],
                model_name=app.get('model', '')[:100],
                is_public=True,
            )
            EloRating.objects.create(submission=sub, contest=arena)
            created += 1

        self.stdout.write(f'seeded {created} new apps ({arena.submissions.count()} total)')

        subs = list(arena.submissions.filter(is_public=True))
        if opts['round_robin']:
            outcomes = run_full_round_robin(subs)
        else:
            outcomes = run_tournament(subs, matches_per_entry=opts['matches'])
        self.stdout.write(f'played {len(outcomes)} AI-judged matches')

        board = (
            EloRating.objects.filter(contest=arena)
            .select_related('submission')
            .order_by('-rating')[:30]
        )
        for i, r in enumerate(board, start=1):
            tag = f"{r.submission.source}:{r.submission.model_name}" if r.submission.source == 'ai' else 'human'
            self.stdout.write(
                f'{i:2d}. {r.rating:4d}  {r.wins}W-{r.losses}L  [{tag}] {r.submission.company_name}'
            )

    def _get_creator(self):
        creator = User.objects.filter(is_superuser=True).first()
        if creator:
            return creator
        creator = User.objects.first()
        if creator:
            return creator
        return User.objects.create_user(username='arena', email='arena@localhost', password='!')
