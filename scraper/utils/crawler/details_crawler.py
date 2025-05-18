import asyncio
from playwright.async_api import async_playwright
import aiohttp
import os
from utils.processing.parsing import *
from utils.processing.geocalc import *


'''
IMAGES
'''

async def download_image(image_url, folder):
    async with aiohttp.ClientSession() as session:
        async with session.get(image_url) as response:
            if response.status == 200:
                filename = os.path.join(folder, image_url.split('/')[-1])
                with open(filename, 'wb') as file:
                    file.write(await response.read())
                print(f"Image saved: {filename}")
            else:
                print(f"Failed to download {image_url}")

async def get_apartment_images(page, timeout,  folder):
    # Ensure the download folder exists
    if not os.path.exists(folder):
        os.makedirs(folder)

    # Click on the cover to reveal images
    cover_element = await page.query_selector('.cover-gradient')
    if cover_element:
        await cover_element.click()
        await page.wait_for_selector('.pmp-image', timeout=timeout)  # Wait for images to load

        # Scrape the images from the revealed gallery
        image_elements = await page.query_selector_all('.pmp-image img')
        image_urls = []
        for img in image_elements:
            img_src = await img.get_attribute('src')
            if img_src:
                image_urls.append(img_src)

        # Download the images asynchronously
        download_tasks = [download_image(url, folder) for url in image_urls]
        await asyncio.gather(*download_tasks)

        print(f"Downloaded {len(image_urls)} images.")
    else:
        print("Could not find the cover element.")

'''
COORDINATES
'''

async def get_marker_offset(page):
    marker = await page.query_selector('img[src="/icons/fr-symbol.svg"]')
    if marker:
        style = await marker.get_attribute("style")
        return extract_translate3d(style)
    return None


async def get_tile_info(page):
    return await page.evaluate('''() => {
        const tile = document.querySelector('.leaflet-tile-loaded');
        if (!tile) return null;
        return {
            url: tile.src,
            transform: tile.style.transform
        };
    }''')


def calculate_marker_coordinates(tile_info, tile_transform, marker_offset):
    url_parts = tile_info['url'].split('/')
    zoom = int(url_parts[-3])
    tile_x = int(url_parts[-2])
    tile_y = int(tile_info['url'].split('/')[-1].split('.')[0].split('@')[0])
    tile_offset_x, tile_offset_y = extract_translate3d(tile_transform)

    global_tile_px_x = tile_x * 256
    global_tile_px_y = tile_y * 256
    map_origin_x = global_tile_px_x - tile_offset_x
    map_origin_y = global_tile_px_y - tile_offset_y

    marker_global_x = map_origin_x + marker_offset[0]
    marker_global_y = map_origin_y + marker_offset[1]
    return pixel_to_latlng(marker_global_x, marker_global_y, zoom)


async def calculate_area_coordinates(page):
    tiles = await page.query_selector_all('.leaflet-tile-loaded')
    centers_x, centers_y = [], []
    zoom = None

    for tile in tiles:
        src = await tile.get_attribute('src')
        style = await tile.get_attribute('style')
        if not src or not style:
            continue

        try:
            url_parts = src.split('/')
            zoom = int(url_parts[-3])
            tile_x = int(url_parts[-2])
            tile_y = int(url_parts[-1].split('.')[0].split('@')[0])
            offset_x, offset_y = extract_translate3d(style)
            global_x = tile_x * 256 - offset_x + 128
            global_y = tile_y * 256 - offset_y + 128
            centers_x.append(global_x)
            centers_y.append(global_y)
        except Exception:
            continue

    if centers_x and centers_y and zoom is not None:
        avg_x = sum(centers_x) / len(centers_x)  + 335 
        avg_y = sum(centers_y) / len(centers_y)
        return pixel_to_latlng(avg_x, avg_y, zoom)
    return None, None

async def get_coordinates(page):
    # Get marker offset (if it exists)
    marker_offset = await get_marker_offset(page)
    if marker_offset:
        # If a marker is found, calculate coordinates based on tile info
        tile_info = await get_tile_info(page)
        if tile_info:
            lat, lng = calculate_marker_coordinates(tile_info, tile_info['transform'], marker_offset)
            print(f"Marker Coordinates:\nLatitude: {lat}\nLongitude: {lng}")
            print(f"https://www.google.com/maps?q={lat},{lng}")
            return lat, lng

    # Fallback if no marker is found
    print("No marker found. Falling back to center of tiles...")
    lat, lng = await calculate_area_coordinates(page)
    if lat is not None and lng is not None:
        print(f"Area Coordinates:\nLatitude: {lat}\nLongitude: {lng}")
        print(f"https://www.google.com/maps?q={lat},{lng}")
        return lat, lng
    else:
        print("Could not calculate Area coordinates.")
        return None, None

'''
TECHNICAL SHEET
'''

async def get_technical_sheet(page, timeout):
    try:
        await page.wait_for_selector('div.technical-sheet', timeout=timeout)

        # Add logging inside the JS
        data = await page.evaluate("""
    () => {
        const sheet = document.querySelector('div.technical-sheet');
        if (!sheet) return { error: "No technical-sheet found" };

        const items = sheet.querySelectorAll('.ant-row');
        console.log("Found technical-sheet with", items.length, "items");

        const result = {};
        items.forEach((item, index) => {
            const labelEl = item.querySelector('span.ant-typography:not([class*=" "])');
            const valueContainer = item.querySelector('.ant-typography.ant-typography-ellipsis.ant-typography-ellipsis-multiple-line');
            const valueEl = valueContainer?.querySelector('strong');

            const label = labelEl?.innerText.trim();
            const value = valueEl?.innerText.trim();

            // Store the label and value (if available) in the result object
            if (label && value) {
                result[label] = value; // Include title as part of the result
            } else {
                console.log(`Item ${index} incomplete — label missing`);
            }
        });

        return result;
    }
""")

        return data

    except Exception as e:
        print(f"Error extracting technical sheet: {e}")
        return None
'''
DESCRIPTION
'''

async def get_description(page, timeout):
    try:
        # Wait for the description element to be available
        await page.wait_for_selector('div.ant-typography.property-description.body.body-regular.body-1.high', timeout=timeout)

        # Capture the description text using evaluate
        description = await page.evaluate("""
            () => {
                const descriptionEl = document.querySelector('div.ant-typography.property-description.body.body-regular.body-1.high span');
                if (!descriptionEl) return { error: "No description found" };
                
                const description = descriptionEl.innerText.trim(); // Get the text inside the span element
                return description;
            }
        """)

        # Log and return the description
        if description and description != "No description found":
            return description
        else:
            return None

    except Exception as e:
        print(f"Error extracting description: {e}")
        return {}

'''
UPLOAD DATE
'''


async def get_upload_date(page, timeout):
    try:
        # Wait for the span element to be available
        await page.wait_for_selector('span.ant-typography[style="font-size:13px"]', timeout=timeout)

        # Capture the fecha ingresada using evaluate
        fecha = await page.evaluate("""
            () => {
                const descriptionEl = document.querySelector('span.ant-typography[style="font-size:13px"]');
                if (!descriptionEl) return { error: "No description found" };

                const text = descriptionEl.innerText.trim(); // Get the text inside the span element
                // Extract the date using regex. This pattern will capture the date format like "5 de abril de 2025"
                const datePattern = /\d{1,2}\sde\s\w+\sde\s\d{4}/;
                const dateMatch = text.match(datePattern);
                return dateMatch ? dateMatch[0] : 'Date not found';
            }
        """)

        # Log and return the fecha ingresada
        if fecha and fecha != "Date not found":
            fecha_dt = parse_date_text(fecha)
            return fecha_dt
        else:
            return None

    except Exception as e:
        print(f"Error extracting fecha ingresada: {e}")
        return {}

'''
FACILITIES
'''

async def get_facilities(page, timeout):
    try:
        # Wait for the property-facilities container
        await page.wait_for_selector('div.property-facilities', timeout=timeout)

        # Evaluate JavaScript to extract the facilities list
        facilities = await page.evaluate("""
            () => {
                const container = document.querySelector('div.property-facilities');
                if (!container) return [];

                const rows = container.querySelectorAll('div.ant-row');
                const result = [];

                rows.forEach((item, index) => {
                    const labelEl = item.querySelector('span.ant-typography:not([class*=" "])');
                    const label = labelEl?.innerText.trim();

                    if (label) {
                        result.push(label);
                    } else {
                        console.log(`${index} not found`);
                    }
                });

                return result;
            }
        """)
        facilities = set(facilities) 
        return facilities

    except Exception as e:
        print(f"Error extracting facilities: {e}")
        return []

'''
ADMINISTRATION VALUE
'''

async def get_admin_value(page, timeout):
    try:
        # Wait for the price tag container to appear 
        await page.wait_for_selector('div.property-price-tag', timeout=timeout)
        # Evaluate JavaScript to extract the administración value
        administracion = await page.evaluate("""
            () => {
                const container = document.querySelector('div.property-price-tag');
                if (!container) return null;

                const adminSpan = container.querySelector('span.commonExpenses');
                if (!adminSpan) return null;

                const text = adminSpan.innerText.trim();
                const match = text.match(/\\$\\s?([\\d.,]+)/);

                if (match && match[1]) {
                    const numericString = match[1].replace(/[.,]/g, '');
                    return parseInt(numericString, 10);
                }

                return null;
            }
        """)
        # Return the extracted administración value
        if administracion is not None:
            return administracion
        else:
            return None
    # Handle any exceptions that occur during the extraction process
    except Exception as e:
        print(f"Error extracting administración value: {e}")
        return None

'''
MAIN FUNCTION
'''

async def scrape_details_page(headless:bool, 
                              proxy:dict, 
                              headers:dict, 
                              url:str, 
                              img_folder:str,
                              timeout:int, 
                              element_timeout:int):

    async with async_playwright() as p:
        browser = await p.chromium.launch(proxy=proxy, headless=headless)
        context = await browser.new_context(extra_http_headers=headers)
        page = await context.new_page()

        try:
            # Step 1: Navigate to the listing page
            await page.goto(url=url, timeout=timeout)
            await page.wait_for_selector('.leaflet-container', timeout=timeout)

            admin_value = await get_admin_value(page, element_timeout)
            facilities = await get_facilities(page, element_timeout)
            upload_date = await get_upload_date(page, element_timeout)
            technical_data = await get_technical_sheet(page, element_timeout)
            description = await get_description(page, element_timeout)
            upload_date = await get_upload_date(page, element_timeout)



            # Step 2: Download the images
            await get_apartment_images(page, element_timeout, img_folder)
            
            # Step 3: Get coordinates from the page
            lat, lng = await get_coordinates(page)
            if lat is None or lng is None:
                print("No coordinates could be found.")
            else:
                coordinates = (lat, lng)
                details = {
                    "coordinates": coordinates,
                    "administracion": admin_value,
                    "facilities": facilities,
                    "upload_date": upload_date,
                    "technical_data": technical_data,
                    "description": description
                }
                print(f"Coordinates successfully extracted: Latitude = {lat}, Longitude = {lng}")
                return details

        except Exception as e:
            print(f"Error during scraping: {e}")
        finally:
            await browser.close()

