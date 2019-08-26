FROM node:12.9.0

RUN npm install express
RUN npm install body-parser

COPY ./app.js /app.js

ENV PORT=3005
CMD ["node", "/app.js"]
