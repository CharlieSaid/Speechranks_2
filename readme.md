How to upload to S3 bucket: 
# Upload files
aws s3 cp to_upload/ s3://speechranks-2.com/ --recursive --cache-control "max-age=3600, public"

Run update file:
/Users/charlie/Desktop/Speechranks_2/venv/bin/python /Users/charlie/Desktop/Speechranks_2/update_data.py


https://docs.aws.amazon.com/AmazonS3/latest/userguide/website-hosting-custom-domain-walkthrough.html#root-domain-walkthrough-create-buckets

To do:
 - Flexible formatting for mobile users - No ability to scroll sideways?
 - Add code to update_data.py that updates the year manifest.
 - Parli Speaker should be an individual event
 - Stop rounding Points!  Show decimals
 - Remove all check images (standardize between Speech and Debate)
 - Tournament mode (Compares tournament data between each other across years)
 - Fix rank-duping bug (hard-code Rank from Points rather than rely on Speechranks)
 - Get nicer fonts
 - LD mode?
 - Head-to-head mode
 - Tournament Simulator:
    - Custom team list creator
    - Simulate prelims OR hard-code seeding to skip to ORs
    - Simulate outrounds (multiple OR structures: 2ORs, 3ORs, NITOC)
 - Search by club or state?
 - Debaters with different clubs screw up club filters.
 - Sort by win % (prelim + overall)
 - Weight ORs more than prelims in win % calculation ("Weighted win %")
 - Winstreak feature?
 - "Qualifying team" filter which removes teams that only have one tournament.
 - Connect tournament data (enable better Rank calculation)
 - Edit Ainsley and I's Texas Escalade 2022 data.
 - Sarah's "5th place in 2021" with Izzy?
 - Jonathan Pattera: "hey bro i love ur new speechranks. in the charts where u have the win rate for each tourney you could also put the total record next to the win rate or something like that"

Known bugs:
 - Levi Cullum: "Hey btw slam is messing with speechranks 2 rn. For example, it's showing my parli rank as 240th, when we're acc 43rd and I'm 240th in slam"
 - Michael Choi: "Awesome speechranks 2, tho i noticed one small bug, thought I'd let you know. Under "Other debate events" the rank for that event is messed up. For example, for us, (michael choi and sam parsons) it shows the correct amount of points we have for parli, but two different ranks, both of which are wrong. It seems to be pulling those ranks from one of our speech category ranks(OO and extemp) , as the points for those speeches match up exactly with the points each of us appear to have for parli. I checked a few other people's pages and the same problem occurred as well"
 - Rachel Shipley: "Hey Charlie! I just checked out speechranks2. It looks great! I really having the win loss record displayed. This always bugged me about speech ranks. I also love the data details on each team. Totally cool!!! I have a few suggestions for further improvement: 1) I noticed on the year navigator button you just had one year (like "2025" instead of "2024-2025"). I think this could be confusing as stoa comp years span two years, especially in the beginning of the year. 2) I miss the green checkmarks. It was always so satisfying to see.  3) Super nit-picky, but I feel like the font you chose for "Speechranks 2" at the top of the page and ariel which you use for everything else clash. In my opinion in makes the page feel a little less professional. Also the header that says "team. state. club. etc." is times new roman and everything else is ariel which bugged my ocd brain 😂  Thanks for all the work you put into this! I think it will be a super useful tool for the leauge."
 - James (huh?): "@Charlie super awesome ngl but what would be nice is if you could give a higher value to OR wins. idk if that's feasible tho"

Critical resources for how I got this working:
 - https://stackoverflow.com/a/50782012
 - Route 53 to get domain name.
 - CloudFront to serve the website.
 - S3 to store the website.
 - Needed a CNAME record for the domain name to point to the CloudFront distribution.  Once this is acquired, there is an option to automatically create a certificate for the domain name in Route 53.
