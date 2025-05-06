# MSSQL Docker Demo with Auto-Restore from Backup

This setup allows you to drop a `.bak` file into `docker/mssql-docker/drop-database-here`, build and run a Docker container that automatically restores the database, creates an admin user, and provides a ready-to-use connection string.

## Steps to Use

1. **Prepare the `.bak` file**  
   Place your desired `.bak` file in the `docker/mssql-docker/drop-database-here` directory.  
   Example: `docker/mssql-docker/drop-database-here/MyNewBackup.bak`

2. **Configure/Change Environment Variables**  
   Adjust the `SA_PASSWORD`, `FULLADMIN_USER`, and `FULLADMIN_PASSWORD` as needed in `.env` file:

3. **Build the Docker Image**  
   - **On x86/AMD64 hosts:**
     ```
     docker build -t mssql-demo .
     ```
   
   - **On ARM64 hosts (e.g., Apple Silicon M1/M2):**
     ```
     docker buildx build --platform linux/amd64 -t mssql-demo .
     ```
     or
     ```
     docker build --platform=linux/amd64 -t mssql-demo .
     ```

4. **Run the Container**  
   - **On x86/AMD64:**
     ```
     docker run -d -p 1433:1433 --name mssql-demo --env-file .env mssql-demo
     ```
   
   - **On ARM64:**
     ```
     docker run -d -p 1433:1433 --name mssql-demo --env-file .env --platform=linux/amd64 mssql-demo
     ```

   The container will:
   - Start SQL Server
   - Discover logical file names from the backup
   - Restore the database automatically
   - Create the admin user from `.env` values
   - Generate a `connection_string.txt` file inside the container

5. **Retrieve the Connection String**  
   To view the connection string:
   ```
   docker exec -it mssql-demo cat /var/opt/mssql/connection_string.txt
   ```

6. **Connect to the Database**  
   Use SQL Server Management Studio, `sqlcmd`, or any preferred method:
   - The connection string in `connection_string.txt` will have the correct database name, `SA` password, and SSL settings.
   - For example:
     ```
     Server=localhost,1433;Database=MyNewBackup;User Id=SA;Password=YourStrong@Passw0rd;Encrypt=true;TrustServerCertificate=true;
     ```

```

**Note for ARM64 users (Apple Silicon/M1/M2):**  
Microsoft SQL Server for Linux does not currently support ARM64 natively. By using `--platform=linux/amd64`, you’re running the image under emulation, which allows the container to run successfully on ARM64 hardware.