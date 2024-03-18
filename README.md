# Data Analysis of Bikeshare Rides In Toronto

An analysis of different publicly available data sources contributing to bike-share trips in Toronto using Tableau.

## Introduction

On September 23, 2022, the City of Toronto announced a Four-Year Growth plan aimed at expanding its existing bike-share network in Toronto. The project aims to cover the entirety of Toronto by having a bike station in each of Toronto’s 25 Wards (a form of the district) [1]. This is expected to add more than 1,000 stations across Toronto, which would add a further 10,000 bikes in the city [1]. Considering this ambitious plan, and having at the time of the report cited an approximate 30% increase in rides from 2022 [1], it is pertinent to analyze existing ridership to understand whether such expansion is justified. Furthermore, it would be important for decision-makers to understand if there are areas that should be of key focus when considering this growth plan. Finally, considering the already existing coverage system, which in itself is a rapid expansion, it would be crucial to understand if the city has in parallel taken measures such that city infrastructure is adapted to ensure the safety of riders and those around them.

The analysis shall be conducted between 2018 and 2022. Whilst it was possible to consider previous years, the data in Q4 2017 is completely missing which could misrepresent the analysis. The trip data is publicly available through the official website of the City of Toronto. In order to properly carry out the analysis, it will be important to understand available stations and bike routes in each ward. It is also important to understand where each ward falls. This will allow for more refined analysis and be able to make granular recommendations. Information such as population, and area is also available for each ward to analyze. The study shall mainly analyze trip data but also make use of other relevant data sources such as weather and accident data. All such information can be leveraged to help make decisions in fleet planning, investment prioritization and maintenance. Furthermore, it could give a broad sense of whether such an expansion is warranted. Finally, it would allow us to analyze current trends in the currently available subscription model to assess its viability. 

## Data Modeling

The data has been modelled using the below logical snowflake schema: 

![alt text](./data/figures/snowflake_schema.png?raw=true)


## Data Cleaning

As the data used were all extracted from public sources, intensive data cleaning is conducted prior to analysis to ensure data compatibility and usability. Specifically:

1 - The Ward Table was sourced from various files that originate from the same location. This includes the population, income, and as well as identification of each ward. Hence, all tables downloaded from the same link needed to be merged by linking each ward to its respective properties. Slight preprocessing needed to be done to the income since it was available with a count available in each income bracket. Hence, the median income group was taken for each ward. Finally, a generic city id column is added. Separately exists a geojson file that allows the geometric mapping of wards in Toronto and bike lanes. The latter is not represented in the schema as it was used as simply a map detailing file only.

2 - The Trip Table is available from the same source as the Wards. The analysis was conducted between 2018 and 2022. **Due to the size of the data, only 8% has been sampled and can be found in the processed data folder**. The actual data would have to be sourced manually from [Toronto Open Data](https://open.toronto.ca/dataset/bike-share-toronto-ridership-data/). There are also several columns to be removed not pertinent to the analysis. Some rows contained improper data and needed to be discarded as well. Furthermore, trips that could not be traced to any specific station were dropped. These represented a very neglibible number of entries. Trips with a duration under a minute were discarded and were assumed to be ”mistake” unlocks of bikes. Trips over 1 hour were also discarded as those could be linked to trips that were not locked back in a station correctly.

3 - The Origin/Destination Table with information about stations was extracted from a public network source as a json file. This file did not contain the foreign key ward id 
so this needed to be determined. Since the coordinates were available and the ward geometric polygon data was available through the geojson, the data could be sptially joined to determine the ward of each station. All stations were successfully matched. Finally, since this network source is live, it also contains tables that were installed in 2023. Hence, to keep the analysis accurate, these stations were discarded. This was done by finding the first time a station was used to start/end a trip and storing this information in a first-use column. Since the trip data is up to 2022, all unmatched stations were considered to be installed after the date of analysis. This date was also used to get some indication of when stations could have been installed. Furthermore, the column capacity contains information about the capacity of each station and is assumed to be static over time (stations could have been upgraded over time). Note that that capacity does not give any indication of the number of available bikes in Toronto.

4 - Weather Table data was first extracted using a publicly authorized scrape (method provided by the data provider) from the official Canadian Government website. The data was scraped for each year separately and was then concatenated together to form one file. Max gust needed to be preprocessed because gusts ≤ 31 were not recorded and stored as a string. This was changed to a speed of 29 km/h since it is not central to the analysis. Furthermore, since only 1% of all weather data was missing, this was filled using linear interpolation. Finally, wind gust categories were created based on the Beaufort scale and a generic city id column was created since this data is only available at a city level.

5 - Accidents Table data is publicly available from the website of the Toronto Police. This data required analysis as there were a large number of  column. Data examples needed to be examined to understand what was pertinent to analysis. Moreover, since coordinates of accidents were available, their location was spatially joined to wards to assign them a ward id. 

Using the logical snowflake schema, the station, ward, weather, city, and accident tables were stored in one Excel file with each table in separate tabs. Due to the size of the trip data, the number of rows of data exceeds the limit of Excel and hence was stored separately in a csv file. The geo-spatial files of wards and bike lines were also stored separately and were linked to the ward table on Tableau easily since the ward id is was readily available in each of those files. These were not included in the schema for both simplicity and since they are only used for map detailing. 

An example Jupyter notebook is available for a more specific review of the preprocessing steps.


## Analysis

The below Analysis provides a snapshot summary of the analysis conducted. For a more interactive story experience as well as additional dashboarding, please refer to the available Tableau file.

### Introduction and Motivation

![alt text](./data/figures/Motivation.png?raw=true)

In 2022, the City of Toronto launched Four Year Growth Plan to expand it’s existing bike-share network to all 25 Wards in Toronto. Considering this ambitious plan, it is worthwhile to examine the existing network of Bikeshare to attempt to pinpoint weaknesses, assess current feasibility, and shed light on factors that could help in the management of the network. Furthermore, it is worthy to analyze the current pricing model of Bikeshare Toronto. There are two types of members in the data: Annual and Casual. The Annual Members pay an annual and benefit from unlimited 30/45 minute trips. Casual members have the pay-as-go option, which charges them based on the duration of the ride plus and unlock fee [2]. They can also buy day passes.

### Casual Members Overtake Annual Members

![alt text](./data/figures/yearly_trip_evolution.png?raw=true)

![alt text](./data/figures/cycling_times.png?raw=true)

There has been a rapid growth in usage by Casual Members in 2020 ( 100% increase!) whereas Annual Member usage has decreased by 20%. Furthermore, as of 2022, Casual Members represent the majority share of trips. There has been a shift in Weekday cycling behaviour after 2020. 08:00, a key peak hour before 2020, significantly dropped making 17:00 - 18:00 the key period for such users. These members have a preference for weekday trips. Before 2022, these members had a clear preference for weekend trips. However, in 2022, these members have no preference for weekend/day trips. Interestingly, the weekday trips of these users in 2022 resemble the behaviour of Annual users.

### And Why Pay for the Annual Pass?

![alt text](./data/figures/weather_1.png?raw=true)

![alt text](./data/figures/weather_2.png?raw=true)

Demand is evidently very seasonal and it seems attractive to ride bikes only during specific periods of the year. Could it be interesting to investigate alternative membership options that leverage this? Furthermore, this bizarre phenomenon of trips increasing with Rainfall seems to be linked to the Temperature more than the rainfall itself. However, considering this trend it is worth noting to ensure the best safety measures are put in place to ensure riders can ride safely during months with heavy rainfall. It is recommended to instead refer to Temperature, Snowfall, or Windspeed to anticipate demand. In fact, there seems to be a strong seasonality in the demand which helps forecast bicycle demand and station allocation.

### So How is Demand Being Served?

![alt text](./data/figures/station_network_plan.png?raw=true)

Before 2020, expansion was only in one region of Toronto. After 2020, expansion began outside but with still constant capacity addition in the main network region. Are these actions justified?

### Yes! Users unsurprisingly love  Spadina-Fort York 

![alt text](./data/figures/station_popularity.png?raw=true)

The Ward Spadina-Fort York is undoubtedly a very popular ward and was seen previously being the ward with the highest number of stations (and hence capacity). As we can see in the above information, the decision to have many stations in this ward is justified considering the stations in this ward are more popular destinations than origins. Furthermore, during the weekend, this ward dominates in both origin and destination and hence fleet management is particularly important then. Interestingly, the station York St/ Queens Quay W is the most popular start and end destination. Since the goal of the plan is to put a station in every ward, it is interesting to investigate the data of actual bike inflow/outflow from these stations to understand if increasing the capacity of existing stations is also key.

### But Popular Station Does Not Mean Popular Route...

![alt text](./data/figures/popular_routes.png?raw=true)

When looking at the top 10 most popular routes, it can be observed that a sizeable amount falls outside of Spadina-Fort york. This is even more significant during the weekend. Since it cannot be directly inferred what is the exact route of the individual from this available data, it is worth understanding the inflow/outflow on specific bike paths to prioritize maintenance and investment in route expansion if needed. In summary, less popular wards have popular routes during the weekend.

## Recommendations

**Network Growth & Subscription Offering:**

The network expansion seems warranted due to the rapid growth of bike use. However:

- Be wary of the dip in use by your Annual Members. Assess revenue from bike share to understand if there is Annual Member churn. In any case, Annual membership does not seem to be an attractive focus option.

- Change in cycling trends seems to be in favour of expansion. Survey riders to understand if Covid-19 has changed preferences and behaviours, if members mainly use bikes for leisure, this could impact the prioritization of investment for expansion.

- Due to the prevalence of strong seasonality in demand and if ridership share between Casual and Annual members persists into 2023, it could be interesting to consider different membership options such as high season, peak hours, etc. Members could benefit from perks such as bike reservations, tailored unlimited ride offers etc.

**Route Optimization and Upgrade:**

Due to demand seasonality, any maintenance and upgrade work is best carried out anytime but the middle of the year. This can be tricky as this also tends to be the period with the harshest weather. The good news is that the main driver of rider demand is temperature rather than necessarily rainfall. Other options include:

- For Spadina-Fort York stations: Partial shutdown and reroute to nearby stations --> should be easy considering it is the ward with the highest number of station capacity

- For stations outside Spadina-Fort York: Observe rider nehaviour to determine the best period to carry out large-scale maintenance/upgrade

- It was seen that a popular station does not imply popular route. Since, this analysis does not specifically know the actual cycle routes taken by riders, a study must be done to confirm whether a popular route means a popular bicycle route. This could help understanding how to maintain/upgrade bicycle paths, especially due to the importance of time (weekday/weekend trend).


## License
This package is licensed under the MIT License. See the LICENSE file for more information.

<br>
<br>
<br>

[1] Toronto Parking Authority. Bike Share Toronto: Four Year Growth Plan. 2022

[2] Bikeshare+Tangerine. Travel the city by bike with bike share Toronto. Accessed: June 20, 2023. [Online]. Available: https://bikesharetoronto.com/pricing/

