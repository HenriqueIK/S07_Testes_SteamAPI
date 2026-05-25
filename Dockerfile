# parte de uma imagem Linux com Node.js já instalado
FROM node:20-alpine

# define /app como pasta de trabalho dentro do container
WORKDIR /app

# copia só os arquivos de dependência primeiro. isso ajuda a aproveitar o cache do Docker, evitando reinstalar dependências se só o código mudou
COPY package.json package-lock.json ./

# instala newman e newman-reporter-htmlextra
RUN npm ci

# copia o restante (coleções Postman, scripts, etc.)
COPY . .

# garante que a pasta de relatórios existe
RUN mkdir -p reports

# comando executado quando o container inicia
CMD ["npm", "run", "test:all"]
