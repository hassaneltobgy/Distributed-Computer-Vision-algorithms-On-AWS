**Overview:**<br>
This project aims to develop a distributed image processing system using cloud computing 
technologies. The system will be implemented in Python, leveraging cloud-based virtual machines for 
distributed computing. The application will use OpenCL or MPI for parallel processing of image data.
Features and Specifications: <br>
• Distributed Processing: The system should be able to distribute image processing tasks across 
multiple virtual machines in the cloud. <br>
• Image Processing Algorithms: Implement various image processing algorithms such as filtering, 
edge detection, and color manipulation. <br>
• Scalability: The system should be scalable, allowing for the addition of more virtual machines as the 
workload increases. <br>
• Fault Tolerance: The system should be resilient to failures, with the ability to reassign tasks from 
failed nodes to operational ones.

# system design
![image](https://github.com/Mazen030/CV-sudoku-solver/assets/93229175/d727b8d4-6178-49ad-ad07-4cfeef52a3cd) <br>
The system implements fault tolerance through a distributed architecture. Initially, four slave nodes operate under the control of a master node. In the event of a slave node failure, the master node seamlessly redirects processing to the remaining functional slaves. This process continues even if additional slave node failures occur, ensuring uninterrupted operation as long as at least two slaves remain available. If all slave nodes become unavailable, a backup slave is automatically detected by the master node, allowing image processing to resume.<br>
We use in this project many AWS services like cloud watch and SNS to monitor the CPU usage of the instances <br>
![image](https://github.com/Mazen030/CV-sudoku-solver/assets/93229175/a3d4ee72-8fed-4de4-90fe-5a70777864e2) <br>
![image](https://github.com/Mazen030/CV-sudoku-solver/assets/93229175/31c6bef0-cb69-4cf6-abf4-8391ee32e60a) <br>
 # special credits to:<br>Hassan Eltobgy, Zeina Hesham ,Mariam Diaa
