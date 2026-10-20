FROM node:22-alpine
WORKDIR /app
COPY package.json package-lock.json ./
COPY application/package.json application/
COPY app-plugin/package.json app-plugin/
RUN npm ci
COPY . .
RUN npm run build
EXPOSE 5173
CMD ["npm", "run", "preview", "--workspace", "application", "--", "--host", "0.0.0.0", "--port", "5173"]
