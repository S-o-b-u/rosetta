@REM ----------------------------------------------------------------------------
@REM Licensed to the Apache Software Foundation (ASF) under one
@REM or more contributor license agreements.  See the NOTICE file
@REM distributed with this work for additional information
@REM regarding copyright ownership.  The ASF licenses this file
@REM to you under the Apache License, Version 2.0 (the
@REM "License"); you may not use this file except in compliance
@REM with the License.  You may obtain a copy of the License at
@REM
@REM   https://www.apache.org/licenses/LICENSE-2.0
@REM
@REM Unless required by applicable law or agreed to in writing,
@REM software distributed under the License is distributed on an
@REM "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
@REM KIND, either express or implied.  See the License for the
@REM specific language governing permissions and limitations
@REM under the License.
@REM ----------------------------------------------------------------------------

@REM Project Rosetta – ATM Rewrite Test
@REM Maven Wrapper Script (Windows)

@IF "%__MVNW_ARG0_NAME__%"=="" (SET "MVN_CMD=mvn.cmd") ELSE (SET "MVN_CMD=%__MVNW_ARG0_NAME__%")

@SET MAVEN_WRAPPER_JAR=%~dp0.mvn\wrapper\maven-wrapper.jar
@SET MAVEN_WRAPPER_PROPERTIES=%~dp0.mvn\wrapper\maven-wrapper.properties

@REM Read distributionUrl from properties file
@FOR /F "tokens=2 delims==" %%A IN ('findstr /i "distributionUrl" "%MAVEN_WRAPPER_PROPERTIES%"') DO @SET DISTRIBUTION_URL=%%A
@FOR /F "tokens=2 delims==" %%A IN ('findstr /i "wrapperVersion" "%MAVEN_WRAPPER_PROPERTIES%"') DO @SET WRAPPER_VERSION=%%A

@REM Determine local Maven home path
@SET MAVEN_HOME=%USERPROFILE%\.m2\wrapper\dists\apache-maven-3.9.9-bin\apache-maven-3.9.9
@SET MVN_EXEC=%MAVEN_HOME%\bin\mvn.cmd

@REM Download Maven if not already present
@IF NOT EXIST "%MVN_EXEC%" (
    @ECHO [Wrapper] Downloading Maven 3.9.9 from Apache servers...
    @MKDIR "%USERPROFILE%\.m2\wrapper\dists\apache-maven-3.9.9-bin" 2>NUL
    @powershell -Command "Invoke-WebRequest -Uri 'https://repo.maven.apache.org/maven2/org/apache/maven/apache-maven/3.9.9/apache-maven-3.9.9-bin.zip' -OutFile '%USERPROFILE%\.m2\wrapper\dists\apache-maven-3.9.9-bin\apache-maven-3.9.9-bin.zip'"
    @powershell -Command "Expand-Archive -Path '%USERPROFILE%\.m2\wrapper\dists\apache-maven-3.9.9-bin\apache-maven-3.9.9-bin.zip' -DestinationPath '%USERPROFILE%\.m2\wrapper\dists\apache-maven-3.9.9-bin' -Force"
    @ECHO [Wrapper] Maven downloaded.
)

@ECHO [Wrapper] Using Maven: %MVN_EXEC%
@"%MVN_EXEC%" %*
