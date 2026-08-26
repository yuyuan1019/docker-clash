
[中文说明](README_zh.md) | **English**

# Zurl

Zurl is a simple and practical short URL system that can quickly generate short links for easy sharing and management. Zurl aims to provide a lightweight solution to help users better manage and track links.

![](https://v.uuu.ovh/imgs/2025/09/12/cf868390221fcfcb.png)

![](https://v.uuu.ovh/imgs/2025/09/12/a7f605b1c7419bf4.png)

## Features

* [x] **Short Link Generation**: Users can convert long URLs into short links for easy sharing and distribution.
* [x] **Link Management**: Provides an intuitive interface where administrators can view, edit, and delete links.
* [x] **Delayed Counting**: The system delays recording click counts for each short link to avoid excessive pressure during high concurrency.
* [x] **Automatic Title Retrieval**: When adding links, the system attempts to automatically retrieve the title of the long URL for easy identification.
* [x] **UA Blocking Support**: Administrators can customize User-Agents to block, preventing malicious access.
* [x] **Data Migration**: Supports migrating YOURLS data to Zurl, helping users transition.
* [x] **API**: Provides API interfaces for secondary development and integration into any system.
* [x] Support for setting short link expiration dates.
* [x] Custom site information
* [x] API Token management
* [x] Bilingual support (Chinese and English)
* [ ] Advanced analytics
* [ ] Login session management

## Installing Zurl

> Currently only Docker installation is supported. Please ensure you have Docker and Docker Compose installed.

Create a new `docker-compose.yaml` file with the following content:

```yaml
version: '3.8'

services:
  zurl:
    container_name: zurl
    image: helloz/zurl
    ports:
      - "3080:3080"
    restart: always
    volumes:
      - ./data:/opt/zurl/app/data
```

Run `docker-compose up -d` to start, then visit `http://IP:3080` and follow the prompts to complete initialization!

**Upgrade**

1. Backup the data in the current mounted directory
2. Stop and remove the current container: `docker-compose down`
3. Pull the latest image: `docker-compose pull`
4. Recreate and start the container: `docker-compose up -d`

> Note: Please be sure to backup your data before upgrading. You are responsible for any data risks caused by upgrades!

## Configuration

**UA Blocking**

You can find `config.toml` in the mounted directory and add User-Agents to block in `app.DENY_UA`. Default blocks:

* *WeChat
* *QQ

> Note: You need to restart the container after modifying the configuration!

**Reset Password**

If you forget your administrator account or password, you can delete the `config.toml` file in the mounted directory, then restart the container and revisit Zurl to complete initialization. (This operation does not affect data)

> Do not delete the `db` directory in the mounted directory, as this will cause link data loss.

## Demo

* Demo site: [https://zurl.demo.mba](https://zurl.demo.mba)
* Username: `xiaoz`
* Password: `blog.xiaoz.org`

## Issue Feedback

* If you have any issues, you can submit them in [Issues](https://github.com/helloxz/zurl/issues).
* Or add my WeChat: `xiaozme`, please be sure to note Zurl

## Tech Stack

* Backend: Python3 + FastAPI
* Frontend: Vue3 + Element Plus
* Database: SQLite3
* Cache: Redis

## Other Products

If you're interested, you can also learn about our other products.

* [Zdir](https://www.zdir.pro/zh/) - A lightweight, multi-functional file sharing program.
* [OneNav](https://www.onenav.top/) - An efficient browser bookmark management tool for centralized bookmark management.
* [ImgURL](https://www.imgurl.org/) - A free image hosting service launched in 2017.
