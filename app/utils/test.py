

"""
formID,SubmissionDateTime,ApplicantName,FatherSpouseName,IncidentDate,lat,longitude,Mobile,IFSCCode,AadhaarNumber,AccountNumber,notes
100,2025-08-21 12:22:05,Gopal Verma,Ram Verma,2025-08-20,22.010000,81.800000,9012345678,ABCD0123456,111122223333,100200300400,"base genuine"
101,2025-08-21 12:25:00,Gopal Verma,Ram Verma,2025-08-20,22.010100,81.800050,9012345678,ABCD0123456,111122223333,100200300400,"exact duplicate -> expect ~1.0"
102,2025-08-21 12:30:00,Gopal Kumar,Ram Verma,2025-08-20,22.010300,81.800200,9012349999,ABCD0123456,111122223333,100200300400,"same aadhaar, different applicant name -> still high"
103,2025-08-21 12:40:00,Gopaal Verma,Ram Verma,2025-08-20,22.020000,81.810000,9012345678,ABCD0123456,222233334444,100200300400,"same mobile, different aadhaar -> medium-high"
104,2025-08-21 13:00:00,Smt. Gopal Verma,Ram Verma,2025-08-20,22.010200,81.800100,7012345678,ABCD0123456,111122223333,100200300400,"name variant (honorific) -> name fuzzy match"
105,2025-08-25 10:00:00,Gopal Verma,Ram Verma,2025-08-01,22.010500,81.800200,9012345678,ABCD0123456,999988887777,200300400500,"incident-submission gap >7 days -> lower date score"
106,2025-08-21 12:50:00,Sunita Devi,Krishna Prasad,2025-08-20,22.500000,82.500000,8877665544,EFGH0987654,333344445555,300400500600,"far away location (>100 km) -> geo score 0"
107,2025-08-21 12:26:00,Same Day Family,Same Day Family,2025-08-20,22.009900,81.799900,9012345678,ABCD0123456,444455556666,100200300400,"same mobile & location & similar names -> potential duplicates on same day"
108,2025-08-21 12:27:00,Gopal Verma,Ram Verma,2025-08-20,22.010050,81.799950,9000005678,ABCD0123456,111122223333,555666777888,"mobile differs by first digits, last4 match -> mobile partial match"
109,2025-08-22 09:00:00,Anil Sharma,Ramesh Sharma,2025-08-20,22.010700,81.800300,9900111222,IJKL1111222,777788889999,999888777666,"same area, different person -> low final"
110,2025-08-21 12:22:10,Gopal Verma,Ram Verma,2025-08-20,22.010020,81.800020,9012345678,ABCD0123456,111122223333,100200300400,"tiny time diff -> should be high (tests datestamp tolerance)"
111,2025-08-21 12:22:05,Gopal Verma,Ram Verma,2025-08-20,22.010000,81.800000,9012345678,ABCD0123456,111122223333,999900001111,"same person but different account -> account mismatch test"
112,2025-08-21 12:22:05,Gopal Verma,Ram Verma,2025-08-20,22.010100,81.800050,0000123456,ABCD0123456,111122223333,100200300400,"leading zero mobile/account cases"
"""



TEST_FORMS = [
    {"formID":"100","SubmissionDateTime":"2025-08-21 12:22:05","ApplicantName":"Gopal Verma","FatherSpouseName":"Ram Verma","IncidentDate":"2025-08-20","lat":"22.010000","longitude":"81.800000","Mobile":"9012345678","IFSCCode":"ABCD0123456","AadhaarNumber":"111122223333","AccountNumber":"100200300400","notes":"base genuine"},
    {"formID":"101","SubmissionDateTime":"2025-08-21 12:25:00","ApplicantName":"Gopal Verma","FatherSpouseName":"Ram Verma","IncidentDate":"2025-08-20","lat":"22.010100","longitude":"81.800050","Mobile":"9012345678","IFSCCode":"ABCD0123456","AadhaarNumber":"111122223333","AccountNumber":"100200300400","notes":"exact duplicate"},
    {"formID":"102","SubmissionDateTime":"2025-08-21 12:30:00","ApplicantName":"Gopal Kumar","FatherSpouseName":"Ram Verma","IncidentDate":"2025-08-20","lat":"22.010300","longitude":"81.800200","Mobile":"9012349999","IFSCCode":"ABCD0123456","AadhaarNumber":"111122223333","AccountNumber":"100200300400","notes":"same aadhaar diff name"},
    {"formID":"103","SubmissionDateTime":"2025-08-21 12:40:00","ApplicantName":"Gopaal Verma","FatherSpouseName":"Ram Verma","IncidentDate":"2025-08-20","lat":"22.020000","longitude":"81.810000","Mobile":"9012345678","IFSCCode":"ABCD0123456","AadhaarNumber":"222233334444","AccountNumber":"100200300400","notes":"same mobile diff aadhaar"},
    {"formID":"104","SubmissionDateTime":"2025-08-21 13:00:00","ApplicantName":"Smt. Gopal Verma","FatherSpouseName":"Ram Verma","IncidentDate":"2025-08-20","lat":"22.010200","longitude":"81.800100","Mobile":"7012345678","IFSCCode":"ABCD0123456","AadhaarNumber":"111122223333","AccountNumber":"100200300400","notes":"honorific name"},
    {"formID":"105","SubmissionDateTime":"2025-08-25 10:00:00","ApplicantName":"Gopal Verma","FatherSpouseName":"Ram Verma","IncidentDate":"2025-08-01","lat":"22.010500","longitude":"81.800200","Mobile":"9012345678","IFSCCode":"ABCD0123456","AadhaarNumber":"999988887777","AccountNumber":"200300400500","notes":"late submission >7d"},
    {"formID":"106","SubmissionDateTime":"2025-08-21 12:50:00","ApplicantName":"Sunita Devi","FatherSpouseName":"Krishna Prasad","IncidentDate":"2025-08-20","lat":"22.500000","longitude":"82.500000","Mobile":"8877665544","IFSCCode":"EFGH0987654","AadhaarNumber":"333344445555","AccountNumber":"300400500600","notes":"far away location"},
    {"formID":"107","SubmissionDateTime":"2025-08-21 12:26:00","ApplicantName":"Same Day Family","FatherSpouseName":"Same Day Family","IncidentDate":"2025-08-20","lat":"22.009900","longitude":"81.799900","Mobile":"9012345678","IFSCCode":"ABCD0123456","AadhaarNumber":"444455556666","AccountNumber":"100200300400","notes":"same mobile & loc"},
    {"formID":"108","SubmissionDateTime":"2025-08-21 12:27:00","ApplicantName":"Gopal Verma","FatherSpouseName":"Ram Verma","IncidentDate":"2025-08-20","lat":"22.010050","longitude":"81.799950","Mobile":"9000005678","IFSCCode":"ABCD0123456","AadhaarNumber":"111122223333","AccountNumber":"555666777888","notes":"mobile last4 match"},
    {"formID":"109","SubmissionDateTime":"2025-08-22 09:00:00","ApplicantName":"Anil Sharma","FatherSpouseName":"Ramesh Sharma","IncidentDate":"2025-08-20","lat":"22.010700","longitude":"81.800300","Mobile":"9900111222","IFSCCode":"IJKL1111222","AadhaarNumber":"777788889999","AccountNumber":"999888777666","notes":"same area different person"},
    {"formID":"110","SubmissionDateTime":"2025-08-21 12:22:10","ApplicantName":"Gopal Verma","FatherSpouseName":"Ram Verma","IncidentDate":"2025-08-20","lat":"22.010020","longitude":"81.800020","Mobile":"9012345678","IFSCCode":"ABCD0123456","AadhaarNumber":"111122223333","AccountNumber":"100200300400","notes":"tiny time diff"},
    {"formID":"111","SubmissionDateTime":"2025-08-21 12:22:05","ApplicantName":"Gopal Verma","FatherSpouseName":"Ram Verma","IncidentDate":"2025-08-20","lat":"22.010000","longitude":"81.800000","Mobile":"9012345678","IFSCCode":"ABCD0123456","AadhaarNumber":"111122223333","AccountNumber":"999900001111","notes":"same person diff account"},
    {"formID":"112","SubmissionDateTime":"2025-08-21 12:22:05","ApplicantName":"Gopal Verma","FatherSpouseName":"Ram Verma","IncidentDate":"2025-08-20","lat":"22.010100","longitude":"81.800050","Mobile":"0000123456","IFSCCode":"ABCD0123456","AadhaarNumber":"111122223333","AccountNumber":"100200300400","notes":"leading zero mobile/account"}
]
