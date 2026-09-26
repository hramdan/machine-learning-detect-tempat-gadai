FROM node:18-alpine

WORKDIR /app

# Copy package descriptors and install dependencies
COPY package*.json ./
RUN npm install

# Copy application source code
COPY . .

# Expose frontend development server port
EXPOSE 3000

# Start SvelteKit development server
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0", "--port", "3000"]
