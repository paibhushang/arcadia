# Arcadia Finance

Arcadia Finance Application

![picture](https://gitlab.com/MattDierick/arcadia-finance/raw/master/Micro%20Services%20architecture.png)

Credentials are admin/iloveblue

//////////////////////

/api is App2

/app3 is App3

/files is the Back End App

//////////////////////

docker network create internal

//////////////////////

docker run -dit -h mainapp --name=mainapp --net=internal registry.gitlab.com/mattdierick/arcadia-finance/mainapp:latest

//////////////////////


docker run -dit -h backend --name=backend --net=internal registry.gitlab.com/mattdierick/arcadia-finance/backend:latest

//////////////////////

docker run -dit -h app2 --name=app2 --net=internal registry.gitlab.com/mattdierick/arcadia-finance/app2:latest

//////////////////////

docker run -dit -h app3 --name=app3 --net=internal registry.gitlab.com/mattdierick/arcadia-finance/app3:latest

//////////////////////

docker run -dit -h nginx --name=nginx --net=internal -p 80:80 -v full_path_to_nginx_conf_file:/etc/nginx/conf.d/default.conf registry.gitlab.com/mattdierick/arcadia-finance/nginx_oss:latest

Use default.conf NGINX file for the NGINX API GW.
