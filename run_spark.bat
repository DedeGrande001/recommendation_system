@echo off
echo Setting Java environment...
set JAVA_HOME=C:\Program Files\Java\jdk-21
set PATH=%JAVA_HOME%\bin;%PATH%

echo.
echo Checking Java version...
java -version

echo.
echo Starting Spark processing...
cd spark_jobs
python movielens_processor.py

pause
