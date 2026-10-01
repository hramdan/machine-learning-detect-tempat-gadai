<script>
	import { onMount } from 'svelte';
	import 'leaflet/dist/leaflet.css';
	import { fetchCabang, triggerScraping, fetchStats, triggerClustering } from '$lib/api.js';

	// State Variables
	let cabangList = [];
	let filteredCabang = [];
	let displayLimit = 60; // Performance optimization for sidebar feed
	let stats = {
		total_branches: 0,
		density_distribution: { Tinggi: 0, Sedang: 0, Rendah: 0 },
		kategori_distribution: {},
		wilayah_distribution: {}
	};

	let selectedWilayah = 'All';
	let selectedKategori = 'All';
	let searchQuery = '';
	let selectedCabang = null;
	let isLoading = false;
	let isScrapingLoading = false;
	let isClusteringLoading = false;
	let toastMessage = null;
	let toastType = 'info'; // 'info' | 'success' | 'error'
	let activeBasemap = 'dark'; // 'dark' | 'osm'
	let is3DTiltActive = false; // 3D Camera Tilt Mode

	// Map Instance & Layers
	let mapContainer;
	let map;
	let markersLayer;
	let darkTileLayer;
	let osmTileLayer;
	let leafletLib;

	// Active Density Layer Filters
	let filterLayers = {
		Tinggi: true,
		Sedang: true,
		Rendah: true,
		Unassigned: true
	};

	// All 10 Administrative Zones across Jabodetabek
	const WILAYAH_OPTIONS = [
		'All',
		'Jakarta Pusat',
		'Jakarta Selatan',
		'Jakarta Timur',
		'Jakarta Barat',
		'Jakarta Utara',
		'Bogor',
		'Depok',
		'Tangerang',
		'Tangerang Selatan',
		'Bekasi'
	];

	const KATEGORI_OPTIONS = [
		'All',
		'BUMN (PT Pegadaian)',
		'Gadai Swasta Berizin',
		'Gadai Mandiri / Lokal'
	];

	// Colors for Density Zones (Radius 1 km Proximity Criteria)
	const ZONE_COLORS = {
		Tinggi: '#ef4444',
		Sedang: '#f59e0b',
		Rendah: '#10b981',
		Unassigned: '#3b82f6'
	};

	const ZONE_GLOWS = {
		Tinggi: 'rgba(239, 68, 68, 0.55)',
		Sedang: 'rgba(245, 158, 11, 0.55)',
		Rendah: 'rgba(16, 185, 129, 0.55)',
		Unassigned: 'rgba(59, 130, 246, 0.55)'
	};

	// Colors for Pawnshop Categories
	const KATEGORI_COLORS = {
		'BUMN (PT Pegadaian)': '#3b82f6',
		'Gadai Swasta Berizin': '#a855f7',
		'Gadai Mandiri / Lokal': '#06b6d4'
	};

	// Region Coordinates Centers for Smooth Camera FlyTo
	const REGION_CENTERS = {
		'Jakarta Pusat': [-6.1805, 106.8284, 13],
		'Jakarta Selatan': [-6.2615, 106.8106, 13],
		'Jakarta Timur': [-6.2250, 106.9004, 13],
		'Jakarta Barat': [-6.1683, 106.7589, 13],
		'Jakarta Utara': [-6.1384, 106.8640, 13],
		'Bogor': [-6.5971, 106.7996, 12.5],
		'Depok': [-6.4025, 106.7942, 13],
		'Tangerang': [-6.1783, 106.6319, 13],
		'Tangerang Selatan': [-6.3075, 106.7082, 13],
		'Bekasi': [-6.2383, 106.9756, 13]
	};

	function showToast(msg, type = 'info', duration = 4000) {
		toastMessage = msg;
		toastType = type;
		setTimeout(() => {
			if (toastMessage === msg) toastMessage = null;
		}, duration);
	}

	onMount(async () => {
		try {
			leafletLib = await import('leaflet');
			const L = leafletLib.default || leafletLib;

			if (!mapContainer) return;

			// Centered on Jabodetabek Regional Core
			map = L.map(mapContainer, {
				center: [-6.24, 106.84],
				zoom: 11,
				minZoom: 8,
				maxZoom: 19,
				zoomControl: false
			});

			L.control.zoom({ position: 'bottomright' }).addTo(map);

			// Dark Basemap
darkTileLayer = L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', {
attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>',
className: 'dark-map-tile',
				maxZoom: 19
			});

			// OSM Basemap
			osmTileLayer = L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', {
				attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>',
				maxZoom: 19
			});

			darkTileLayer.addTo(map);
			markersLayer = L.layerGroup().addTo(map);

			setTimeout(() => { if (map) map.invalidateSize(); }, 150);
			setTimeout(() => { if (map) map.invalidateSize(); }, 600);

			window.addEventListener('resize', () => {
				if (map) map.invalidateSize();
			});

			await loadData();
		} catch (err) {
			console.error('Error initializing map:', err);
			showToast('Gagal memuat peta interaktif.', 'error');
		}
	});

	function switchBasemap(type) {
		activeBasemap = type;
		if (!map || !darkTileLayer || !osmTileLayer) return;

		if (type === 'dark') {
			map.removeLayer(osmTileLayer);
			darkTileLayer.addTo(map);
		} else {
			map.removeLayer(darkTileLayer);
			osmTileLayer.addTo(map);
		}
	}

	function toggle3DTilt() {
		is3DTiltActive = !is3DTiltActive;
		showToast(is3DTiltActive ? 'Mode 3D Pitch Aktif' : 'Mode 2D Overview Aktif', 'info', 2000);
		setTimeout(() => {
			if (map) map.invalidateSize();
		}, 300);
	}

	async function loadData() {
		isLoading = true;
		try {
			const [branchesData, statsData] = await Promise.allSettled([
				fetchCabang(
					selectedWilayah === 'All' ? '' : selectedWilayah,
					selectedKategori === 'All' ? '' : selectedKategori
				),
				fetchStats()
			]);

			if (branchesData.status === 'fulfilled' && branchesData.value && branchesData.value.length > 0) {
				cabangList = branchesData.value;
				applyFilters();
			} else {
				// Trigger mass-scale scraping if database is currently empty
				await handleTriggerScraping(true);
			}

			if (statsData.status === 'fulfilled') {
				stats = statsData.value || stats;
			}
		} catch (err) {
			console.error('Error loading data:', err);
		} finally {
			isLoading = false;
		}
	}

	function getAccurateGmapsUrl(cabang) {
		if (cabang?.google_maps_url) return cabang.google_maps_url;
		const query = [cabang?.nama, cabang?.alamat, cabang?.wilayah].filter(Boolean).join(' ');
		return `https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(query)}`;
	}

	function applyFilters() {
		displayLimit = 60; // Reset pagination window
		filteredCabang = cabangList.filter((item) => {
			// Wilayah Filter
			const matchesWilayah =
				selectedWilayah === 'All' ||
				(item.wilayah && item.wilayah.toLowerCase().includes(selectedWilayah.toLowerCase()));

			// Kategori Filter
			const itemKat = item.kategori || 'BUMN (PT Pegadaian)';
			const matchesKategori =
				selectedKategori === 'All' ||
				itemKat.toLowerCase().includes(selectedKategori.toLowerCase());

			// Search Query Filter
			const matchesSearch =
				!searchQuery.trim() ||
				(item.nama && item.nama.toLowerCase().includes(searchQuery.toLowerCase())) ||
				(item.alamat && item.alamat.toLowerCase().includes(searchQuery.toLowerCase()));

			// Density Zone Toggle Filter
			const zone = item.density_zone || 'Unassigned';
			const matchesZone = filterLayers[zone] !== false;

			return matchesWilayah && matchesKategori && matchesSearch && matchesZone;
		});

		renderMarkers();
	}

	function renderMarkers() {
		if (!map || !markersLayer || !leafletLib) return;
		const L = leafletLib.default || leafletLib;

		markersLayer.clearLayers();

		filteredCabang.forEach((cabang) => {
			const lat = parseFloat(cabang.lat);
			const lng = parseFloat(cabang.lng);

			if (!isNaN(lat) && !isNaN(lng)) {
				const zone = cabang.density_zone || 'Unassigned';
				const color = ZONE_COLORS[zone] || ZONE_COLORS.Unassigned;
				const glow = ZONE_GLOWS[zone] || ZONE_GLOWS.Unassigned;
				const kat = cabang.kategori || 'BUMN (PT Pegadaian)';
				const katColor = KATEGORI_COLORS[kat] || '#38bdf8';
				const neighbors = cabang.neighbor_count || 0;

				// Custom HTML Pulsing Marker
				const customIcon = L.divIcon({
					className: 'custom-spatial-marker',
					html: `
						<div class="marker-container" style="--zone-color: ${color}; --zone-glow: ${glow};">
							<div class="marker-pulse"></div>
							<div class="marker-core">
								<span class="marker-metric">${neighbors}</span>
							</div>
						</div>
					`,
					iconSize: [28, 28],
					iconAnchor: [14, 14],
					popupAnchor: [0, -14]
				});

				const marker = L.marker([lat, lng], { icon: customIcon });

				// Glassmorphism Popup Card
				const gmapsUrl = getAccurateGmapsUrl(cabang);
				const popupContent = `
					<div class="spatial-popup-card">
						<div class="popup-badges-row">
							<span class="popup-badge" style="background: ${color}25; color: ${color}; border: 1px solid ${color}66;">
								Zona ${zone} (${neighbors} Tetangga / 1 km)
							</span>
							<span class="popup-kat-badge" style="background: ${katColor}25; color: ${katColor}; border: 1px solid ${katColor}66;">
								${kat}
							</span>
						</div>
						<h4 class="popup-title">${cabang.nama}</h4>
						<p class="popup-address">${cabang.alamat}</p>
						<div class="popup-meta">
							<span class="popup-region">📍 ${cabang.wilayah || 'Jabodetabek'}</span>
							<span class="popup-coords">${lat.toFixed(4)}, ${lng.toFixed(4)}</span>
						</div>
						<a
							href="${gmapsUrl}"
							target="_blank"
							rel="noopener noreferrer"
							class="popup-gmaps-btn"
						>
							<svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
								<polygon points="3 11 22 2 13 21 11 13 3 11"></polygon>
							</svg>
							<span>Buka di Google Maps</span>
							<svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
								<path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"></path>
								<polyline points="15 3 21 3 21 9"></polyline>
								<line x1="10" y1="14" x2="21" y2="3"></line>
							</svg>
						</a>
					</div>
				`;

				marker.bindPopup(popupContent, {
					className: 'spatial-custom-popup',
					maxWidth: 320
				});

				marker.on('click', () => {
					selectedCabang = cabang;
					focusCabang(cabang, false);
				});

				markersLayer.addLayer(marker);
			}
		});
	}

	function focusCabang(cabang, openPopup = true) {
		selectedCabang = cabang;
		const lat = parseFloat(cabang.lat);
		const lng = parseFloat(cabang.lng);

		if (map && !isNaN(lat) && !isNaN(lng)) {
			map.flyTo([lat, lng], 15.5, {
				duration: 1.2,
				easeLinearity: 0.25
			});

			if (openPopup) {
				setTimeout(() => {
					markersLayer.eachLayer((layer) => {
						const latLng = layer.getLatLng();
						if (
							Math.abs(latLng.lat - lat) < 0.0001 &&
							Math.abs(latLng.lng - lng) < 0.0001
						) {
							layer.openPopup();
						}
					});
				}, 1250);
			}
		}
	}

	function resetMapView() {
		if (map) {
			map.flyTo([-6.24, 106.84], 11, { duration: 1.0 });
			selectedCabang = null;
		}
	}

	async function handleTriggerScraping(isInitialSilent = false) {
		if (isScrapingLoading) return;
		isScrapingLoading = true;
		if (!isInitialSilent) {
			showToast('Memulai crawling massal seluruh tempat gadai se-Jabodetabek...', 'info');
		}

		try {
			const res = await triggerScraping();
			showToast(`Scraping Massal Berhasil! ${res.total_count} tempat gadai dipetakan & dihitung radius 1 km.`, 'success');
			await loadData();
			const statsRes = await fetchStats();
			stats = statsRes;
		} catch (err) {
			console.error('Scraping failure:', err);
			showToast(`Gagal scraping: ${err.message}`, 'error');
		} finally {
			isScrapingLoading = false;
		}
	}

	async function handleTriggerClustering() {
		if (isClusteringLoading) return;
		isClusteringLoading = true;
		showToast('Menjalankan ulang analisis spasial kedekatan 1 km...', 'info');

		try {
			await triggerClustering();
			showToast('Analisis kedekatan spasial 1 km berhasil diperbarui!', 'success');
			await loadData();
		} catch (err) {
			console.error('Clustering failure:', err);
			showToast(`Gagal clustering: ${err.message}`, 'error');
		} finally {
			isClusteringLoading = false;
		}
	}

	function handleWilayahChange(wilayah) {
		selectedWilayah = wilayah;
		applyFilters();

		if (wilayah === 'All') {
			resetMapView();
		} else if (REGION_CENTERS[wilayah] && map) {
			const [rLat, rLng, rZoom] = REGION_CENTERS[wilayah];
			map.flyTo([rLat, rLng], rZoom, { duration: 1.1 });
		} else if (filteredCabang.length > 0) {
			const firstWithCoords = filteredCabang.find((c) => c.lat && c.lng);
			if (firstWithCoords && map) {
				map.flyTo([parseFloat(firstWithCoords.lat), parseFloat(firstWithCoords.lng)], 13, { duration: 1.0 });
			}
		}
	}

	function handleKategoriChange(kategori) {
		selectedKategori = kategori;
		applyFilters();
	}

	function toggleDensityLayer(zone) {
		filterLayers[zone] = !filterLayers[zone];
		applyFilters();
	}

	function loadMoreCards() {
		displayLimit += 60;
	}

	// Reactive triggers
	$: searchQuery, applyFilters();
</script>

<svelte:head>
	<title>Jabodetabek Pawnshop Spatial AI | Pemetaan & Analisis 1 km</title>
</svelte:head>

<div class="app-layout">
	<!-- 1. LEFT GLASSMORPHISM SIDEBAR (380px) -->
	<aside class="sidebar-panel">
		<!-- Brand & Header -->
		<header class="brand-header">
			<div class="brand-badge-row">
				<div class="live-status-pill">
					<span class="live-indicator"></span>
					<span>Mass-Scale Spatial AI</span>
				</div>
				<span class="telemetry-tag">RADIUS 1 KM PROXIMITY</span>
			</div>
			<div class="brand-title-wrap">
				<div class="brand-icon">
					<svg viewBox="0 0 24 24" width="22" height="22" fill="none" stroke="currentColor" stroke-width="2">
						<circle cx="12" cy="12" r="10" />
						<polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2" />
					</svg>
				</div>
				<div>
					<h1 class="brand-title">JABODETABEK GADAI</h1>
					<p class="brand-subtitle">Pemetaan Massal Seluruh Tempat Gadai</p>
				</div>
			</div>
		</header>

		<!-- Spatial Analytics Summary Cards -->
		<section class="stats-overview">
			<div class="stat-card">
				<span class="stat-label">Total Gerai</span>
				<span class="stat-value">{stats.total_branches || filteredCabang.length}</span>
			</div>
			<div class="stat-card">
				<span class="stat-label">Tinggi (≥5 / 1km)</span>
				<span class="stat-value highlight-red">{stats.density_distribution?.Tinggi || 0}</span>
			</div>
			<div class="stat-card">
				<span class="stat-label">Sedang / Rendah</span>
				<span class="stat-value highlight-amber">
					{(stats.density_distribution?.Sedang || 0) + (stats.density_distribution?.Rendah || 0)}
				</span>
			</div>
		</section>

		<!-- Action Trigger CTA -->
		<div class="cta-section">
			<button
				id="btn-scrape"
				class="btn-primary-action"
				on:click={() => handleTriggerScraping(false)}
				disabled={isScrapingLoading}
			>
				{#if isScrapingLoading}
					<div class="action-spinner"></div>
					<span>Crawling Massal Se-Jabodetabek...</span>
				{:else}
					<svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2">
						<path d="M21.5 2v6h-6M21.34 15.57a10 10 0 1 1-.57-8.38l5.67-5.67" />
					</svg>
					<span>Jalankan Scraping Otomatis</span>
				{/if}
			</button>
		</div>

		<!-- Search Bar -->
		<div class="search-box-wrap">
			<div class="search-input-inner">
				<svg class="search-icon" viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2">
					<circle cx="11" cy="11" r="8" />
					<line x1="21" y1="21" x2="16.65" y2="16.65" />
				</svg>
				<input
					id="search-input"
					type="text"
					placeholder="Cari tempat gadai, brand, atau alamat..."
					bind:value={searchQuery}
				/>
				{#if searchQuery}
					<button class="clear-search-btn" on:click={() => (searchQuery = '')}>×</button>
				{/if}
			</div>
		</div>

		<!-- Category Filter Pills -->
		<div class="category-filter-bar">
			<span class="filter-caption">Kategori:</span>
			<div class="category-pills">
				{#each KATEGORI_OPTIONS as kat}
					<button
						class="pill-btn kat-pill {selectedKategori === kat ? 'active' : ''}"
						on:click={() => handleKategoriChange(kat)}
					>
						{kat === 'All' ? 'Semua' : kat}
					</button>
				{/each}
			</div>
		</div>

		<!-- Regional Filter Pills across all 10 Jabodetabek territories -->
		<div class="region-filter-bar">
			<span class="filter-caption">Wilayah Administrasi:</span>
			<div class="region-pills">
				{#each WILAYAH_OPTIONS as opt}
					<button
						class="pill-btn {selectedWilayah === opt ? 'active' : ''}"
						on:click={() => handleWilayahChange(opt)}
					>
						{opt}
					</button>
				{/each}
			</div>
		</div>

		<!-- Feed Header -->
		<div class="feed-header">
			<span class="feed-count-label">Menampilkan <strong>{filteredCabang.length}</strong> Titik Gadai</span>
			<button class="recluster-btn" on:click={handleTriggerClustering} title="Hitung Ulang Analisis Kedekatan 1 km">
				{#if isClusteringLoading}
					<span class="mini-spinner"></span>
				{:else}
					<span>⚡ Proximity 1 km</span>
				{/if}
			</button>
		</div>

		<!-- Pawnshop Feed List (Optimized for hundreds of outlets) -->
		<div class="branch-feed-list">
			{#if isLoading}
				<div class="feed-loading-state">
					<div class="pulse-loader"></div>
					<p>Memuat ratusan titik tempat gadai se-Jabodetabek...</p>
				</div>
			{:else if filteredCabang.length === 0}
				<div class="feed-empty-state">
					<p>Tidak ada tempat gadai ditemukan untuk filter ini.</p>
					<button class="btn-reset-filters" on:click={() => { selectedWilayah = 'All'; selectedKategori = 'All'; searchQuery = ''; }}>
						Reset Filter
					</button>
				</div>
			{:else}
				{#each filteredCabang.slice(0, displayLimit) as cabang (cabang.id || cabang.nama)}
					{@const kat = cabang.kategori || 'BUMN (PT Pegadaian)'}
					{@const katColor = KATEGORI_COLORS[kat] || '#38bdf8'}
					{@const neighbors = cabang.neighbor_count || 0}
					<div
						class="branch-item-card {selectedCabang?.id === cabang.id ? 'selected' : ''}"
						on:click={() => focusCabang(cabang, true)}
						role="button"
						tabindex="0"
						on:keydown={(e) => e.key === 'Enter' && focusCabang(cabang, true)}
					>
						<div class="card-top-row">
							<h3 class="branch-name">{cabang.nama}</h3>
							<span
								class="density-badge"
								style="
									background: {ZONE_COLORS[cabang.density_zone] || ZONE_COLORS.Unassigned}20;
									color: {ZONE_COLORS[cabang.density_zone] || ZONE_COLORS.Unassigned};
									border: 1px solid {ZONE_COLORS[cabang.density_zone] || ZONE_COLORS.Unassigned}55;
								"
							>
								{cabang.density_zone || 'Unassigned'} ({neighbors} dlm 1km)
							</span>
						</div>

						<p class="branch-address">{cabang.alamat}</p>

						<div class="card-footer-meta">
							<div class="meta-left">
								<span
									class="kat-tag"
									style="color: {katColor}; background: {katColor}16; border: 1px solid {katColor}40;"
								>
									{kat}
								</span>
								<span class="region-tag">📍 {cabang.wilayah || 'Jabodetabek'}</span>
							</div>
							{#if cabang.lat && cabang.lng}
								<div class="meta-right">
									<a
										href={getAccurateGmapsUrl(cabang)}
										target="_blank"
										rel="noopener noreferrer"
										class="card-gmaps-btn"
										on:click|stopPropagation
										title="Buka rute di Google Maps"
									>
										<svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
											<polygon points="3 11 22 2 13 21 11 13 3 11"></polygon>
										</svg>
										<span>Maps</span>
										<svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
											<path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"></path>
											<polyline points="15 3 21 3 21 9"></polyline>
										</svg>
									</a>
								</div>
							{/if}
						</div>
					</div>
				{/each}

				{#if filteredCabang.length > displayLimit}
					<div class="load-more-wrap">
						<button class="btn-load-more" on:click={loadMoreCards}>
							Tampilkan Lebih Banyak ({displayLimit} dari {filteredCabang.length})
						</button>
					</div>
				{/if}
			{/if}
		</div>
	</aside>

	<!-- 2. MAIN INTERACTIVE 3D SPATIAL MAP CONTAINER -->
	<main class="map-viewport {is3DTiltActive ? 'tilt-3d-active' : ''}">
		<div id="map-container" bind:this={mapContainer}></div>

		<!-- Floating HUD Telemetry Overlay (Top Right) -->
		<div class="map-hud-panel">
			<div class="hud-header">
				<span class="hud-title">SPATIAL TELEMETRY (RADIUS 1 KM)</span>
				<div class="hud-header-actions">
					<button
						class="btn-hud-map-switch {is3DTiltActive ? 'active' : ''}"
						on:click={toggle3DTilt}
						title="Toggle 3D Pitch / Perspective Camera Tilt"
					>
						3D Tilt
					</button>
					<button
						class="btn-hud-map-switch {activeBasemap === 'dark' ? 'active' : ''}"
						on:click={() => switchBasemap('dark')}
						title="Tema Gelap"
					>
						Dark
					</button>
					<button
						class="btn-hud-map-switch {activeBasemap === 'osm' ? 'active' : ''}"
						on:click={() => switchBasemap('osm')}
						title="Tema Terang (OSM)"
					>
						OSM
					</button>
					<button class="btn-hud-reset" on:click={resetMapView} title="Reset camera view to Jabodetabek">
						<svg viewBox="0 0 24 24" width="13" height="13" fill="none" stroke="currentColor" stroke-width="2">
							<path d="M3 12a9 9 0 1 0 9-9 9.75 9.75 0 0 0-6.74 2.74L3 8" />
							<path d="M3 3v5h5" />
						</svg>
						<span>Reset</span>
					</button>
				</div>
			</div>

			<!-- Density Zone Layer Toggles -->
			<div class="hud-layers">
				<button
					class="layer-toggle {filterLayers.Tinggi ? 'active' : ''}"
					style="--zone-color: {ZONE_COLORS.Tinggi}"
					on:click={() => toggleDensityLayer('Tinggi')}
				>
					<span class="layer-dot" style="background: {ZONE_COLORS.Tinggi}"></span>
					<span>Tinggi (≥5): {stats.density_distribution?.Tinggi || 0}</span>
				</button>

				<button
					class="layer-toggle {filterLayers.Sedang ? 'active' : ''}"
					style="--zone-color: {ZONE_COLORS.Sedang}"
					on:click={() => toggleDensityLayer('Sedang')}
				>
					<span class="layer-dot" style="background: {ZONE_COLORS.Sedang}"></span>
					<span>Sedang (2-4): {stats.density_distribution?.Sedang || 0}</span>
				</button>

				<button
					class="layer-toggle {filterLayers.Rendah ? 'active' : ''}"
					style="--zone-color: {ZONE_COLORS.Rendah}"
					on:click={() => toggleDensityLayer('Rendah')}
				>
					<span class="layer-dot" style="background: {ZONE_COLORS.Rendah}"></span>
					<span>Rendah (&lt;2): {stats.density_distribution?.Rendah || 0}</span>
				</button>
			</div>

			<!-- Density Distribution Progress Bar -->
			<div class="hud-bar-wrap">
				<div class="hud-bar-label">
					<span>Distribusi Kepadatan (Radius 1 km)</span>
					<span>{stats.total_branches || filteredCabang.length} Titik</span>
				</div>
				<div class="multi-progress-bar">
					{#if (stats.total_branches || filteredCabang.length) > 0}
						{@const total = stats.total_branches || filteredCabang.length}
						<div
							class="bar-segment"
							style="width: {((stats.density_distribution?.Tinggi || 0) / total) * 100}%; background: {ZONE_COLORS.Tinggi};"
							title="Tinggi (≥ 5 tetangga)"
						></div>
						<div
							class="bar-segment"
							style="width: {((stats.density_distribution?.Sedang || 0) / total) * 100}%; background: {ZONE_COLORS.Sedang};"
							title="Sedang (2-4 tetangga)"
						></div>
						<div
							class="bar-segment"
							style="width: {((stats.density_distribution?.Rendah || 0) / total) * 100}%; background: {ZONE_COLORS.Rendah};"
							title="Rendah (< 2 tetangga)"
						></div>
					{:else}
						<div class="bar-segment" style="width: 100%; background: #334155;"></div>
					{/if}
				</div>
			</div>
		</div>

		<!-- Floating Detail Drawer for Selected Pawnshop -->
		{#if selectedCabang}
			<div class="floating-detail-drawer">
				<div class="drawer-header">
					<div class="drawer-badges">
						<span
							class="density-badge"
							style="
								background: {ZONE_COLORS[selectedCabang.density_zone] || ZONE_COLORS.Unassigned}25;
								color: {ZONE_COLORS[selectedCabang.density_zone] || ZONE_COLORS.Unassigned};
								border: 1px solid {ZONE_COLORS[selectedCabang.density_zone] || ZONE_COLORS.Unassigned}66;
							"
						>
							Zona {selectedCabang.density_zone || 'Unassigned'} ({selectedCabang.neighbor_count || 0} Tetangga / 1 km)
						</span>
						<span
							class="kat-badge"
							style="
								background: {KATEGORI_COLORS[selectedCabang.kategori] || '#38bdf8'}25;
								color: {KATEGORI_COLORS[selectedCabang.kategori] || '#38bdf8'};
								border: 1px solid {KATEGORI_COLORS[selectedCabang.kategori] || '#38bdf8'}66;
							"
						>
							{selectedCabang.kategori || 'BUMN (PT Pegadaian)'}
						</span>
					</div>
					<button class="btn-close-drawer" on:click={() => (selectedCabang = null)} title="Tutup">✕</button>
				</div>
				<h3 class="drawer-title">{selectedCabang.nama}</h3>
				<p class="drawer-address">{selectedCabang.alamat}</p>
				<div class="drawer-actions">
					<span class="drawer-region">📍 {selectedCabang.wilayah || 'Jabodetabek'}</span>
					<a
						href={getAccurateGmapsUrl(selectedCabang)}
						target="_blank"
						rel="noopener noreferrer"
						class="btn-drawer-gmaps"
					>
						<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
							<polygon points="3 11 22 2 13 21 11 13 3 11"></polygon>
						</svg>
						<span>Buka di Google Maps</span>
						<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
							<path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"></path>
							<polyline points="15 3 21 3 21 9"></polyline>
						</svg>
					</a>
				</div>
			</div>
		{/if}

		<!-- Toast Notification Banner -->
		{#if toastMessage}
			<div class="toast-banner {toastType}">
				<span class="toast-indicator"></span>
				<span class="toast-text">{toastMessage}</span>
				<button class="toast-close" on:click={() => (toastMessage = null)}>×</button>
			</div>
		{/if}
	</main>
</div>

<style>
:global(.dark-map-tile) {
filter: grayscale(1) invert(1) brightness(0.8) contrast(0.9);
}

	/* Layout Core */
	.app-layout {
		display: flex;
		width: 100vw;
		height: 100vh;
		background-color: #0b0f19;
		overflow: hidden;
		position: relative;
	}

	/* 380px Glassmorphism Sidebar */
	.sidebar-panel {
		width: 380px;
		min-width: 380px;
		height: 100%;
		background: rgba(15, 23, 42, 0.84);
		backdrop-filter: blur(20px);
		-webkit-backdrop-filter: blur(20px);
		border-right: 1px solid rgba(255, 255, 255, 0.08);
		display: flex;
		flex-direction: column;
		z-index: 1000;
		box-shadow: 10px 0 30px rgba(0, 0, 0, 0.5);
		transition: transform 0.3s ease;
	}

	.brand-header {
		padding: 16px 20px 12px;
		border-bottom: 1px solid rgba(255, 255, 255, 0.06);
	}

	.brand-badge-row {
		display: flex;
		align-items: center;
		justify-content: space-between;
		margin-bottom: 8px;
	}

	.live-status-pill {
		display: inline-flex;
		align-items: center;
		gap: 6px;
		background: rgba(16, 185, 129, 0.12);
		border: 1px solid rgba(16, 185, 129, 0.3);
		padding: 3px 8px;
		border-radius: 9999px;
		font-size: 0.68rem;
		font-weight: 600;
		color: #34d399;
	}

	.live-indicator {
		width: 6px;
		height: 6px;
		border-radius: 50%;
		background: #10b981;
		box-shadow: 0 0 8px #10b981;
		animation: pulse-ring 2s infinite;
	}

	.telemetry-tag {
		font-family: 'JetBrains Mono', monospace;
		font-size: 0.62rem;
		color: #64748b;
		letter-spacing: 0.05em;
	}

	.brand-title-wrap {
		display: flex;
		align-items: center;
		gap: 12px;
	}

	.brand-icon {
		width: 40px;
		height: 40px;
		border-radius: 10px;
		background: linear-gradient(135deg, #1e40af, #3b82f6);
		display: flex;
		align-items: center;
		justify-content: center;
		color: #ffffff;
		box-shadow: 0 0 15px rgba(59, 130, 246, 0.4);
	}

	.brand-title {
		font-size: 1.1rem;
		font-weight: 800;
		letter-spacing: 0.05em;
		background: linear-gradient(90deg, #ffffff, #93c5fd);
		-webkit-background-clip: text;
		background-clip: text;
		-webkit-text-fill-color: transparent;
		line-height: 1.1;
	}

	.brand-subtitle {
		font-size: 0.68rem;
		color: #94a3b8;
		margin-top: 2px;
	}

	/* Stats Overview */
	.stats-overview {
		display: grid;
		grid-template-columns: repeat(3, 1fr);
		gap: 8px;
		padding: 10px 20px;
		background: rgba(0, 0, 0, 0.2);
		border-bottom: 1px solid rgba(255, 255, 255, 0.04);
	}

	.stat-card {
		background: rgba(30, 41, 59, 0.5);
		border: 1px solid rgba(255, 255, 255, 0.05);
		border-radius: 8px;
		padding: 7px 9px;
		display: flex;
		flex-direction: column;
	}

	.stat-label {
		font-size: 0.6rem;
		color: #94a3b8;
		text-transform: uppercase;
		letter-spacing: 0.04em;
	}

	.stat-value {
		font-size: 1.05rem;
		font-weight: 700;
		color: #f8fafc;
		font-family: 'JetBrains Mono', monospace;
		margin-top: 2px;
	}

	.highlight-red { color: #f87171; }
	.highlight-amber { color: #fbbf24; }

	/* Action CTA Section */
	.cta-section {
		padding: 10px 20px;
	}

	.btn-primary-action {
		width: 100%;
		display: flex;
		align-items: center;
		justify-content: center;
		gap: 8px;
		background: linear-gradient(135deg, #2563eb, #1d4ed8);
		border: 1px solid rgba(96, 165, 250, 0.3);
		color: #ffffff;
		padding: 10px 16px;
		border-radius: 10px;
		font-size: 0.82rem;
		font-weight: 600;
		cursor: pointer;
		transition: all 0.2s ease;
		box-shadow: 0 4px 14px rgba(37, 99, 235, 0.35);
	}

	.btn-primary-action:hover:not(:disabled) {
		background: linear-gradient(135deg, #3b82f6, #2563eb);
		transform: translateY(-1px);
		box-shadow: 0 6px 20px rgba(59, 130, 246, 0.5);
	}

	.btn-primary-action:disabled {
		opacity: 0.7;
		cursor: not-allowed;
	}

	.action-spinner {
		width: 15px;
		height: 15px;
		border: 2px solid rgba(255, 255, 255, 0.3);
		border-top-color: #ffffff;
		border-radius: 50%;
		animation: spin 0.8s linear infinite;
	}

	/* Search Box */
	.search-box-wrap {
		padding: 0 20px 8px;
	}

	.search-input-inner {
		position: relative;
		display: flex;
		align-items: center;
		background: rgba(15, 23, 42, 0.6);
		border: 1px solid rgba(255, 255, 255, 0.1);
		border-radius: 8px;
		padding: 0 10px;
	}

	.search-input-inner:focus-within {
		border-color: #3b82f6;
		box-shadow: 0 0 0 2px rgba(59, 130, 246, 0.2);
	}

	.search-icon {
		color: #64748b;
		margin-right: 8px;
	}

	.search-input-inner input {
		width: 100%;
		background: transparent;
		border: none;
		outline: none;
		color: #f8fafc;
		font-size: 0.8rem;
		padding: 7px 0;
	}

	.clear-search-btn {
		background: none;
		border: none;
		color: #94a3b8;
		font-size: 1.1rem;
		cursor: pointer;
	}

	/* Category & Region Filter Bars */
	.category-filter-bar,
	.region-filter-bar {
		padding: 0 20px 8px;
		display: flex;
		flex-direction: column;
		gap: 4px;
	}

	.filter-caption {
		font-size: 0.6rem;
		color: #64748b;
		text-transform: uppercase;
		font-weight: 600;
		letter-spacing: 0.05em;
	}

	.category-pills,
	.region-pills {
		display: flex;
		gap: 5px;
		overflow-x: auto;
		padding-bottom: 2px;
		scrollbar-width: none;
	}

	.category-pills::-webkit-scrollbar,
	.region-pills::-webkit-scrollbar {
		display: none;
	}

	.pill-btn {
		background: rgba(30, 41, 59, 0.6);
		border: 1px solid rgba(255, 255, 255, 0.06);
		color: #94a3b8;
		padding: 3px 8px;
		border-radius: 6px;
		font-size: 0.68rem;
		white-space: nowrap;
		cursor: pointer;
		transition: all 0.15s ease;
	}

	.pill-btn:hover {
		color: #f8fafc;
		background: rgba(51, 65, 85, 0.8);
	}

	.pill-btn.active {
		background: rgba(59, 130, 246, 0.2);
		border-color: #3b82f6;
		color: #60a5fa;
		font-weight: 600;
	}

	.kat-pill.active {
		background: rgba(168, 85, 247, 0.25);
		border-color: #a855f7;
		color: #d8b4fe;
	}

	/* Feed Header */
	.feed-header {
		padding: 8px 20px;
		display: flex;
		align-items: center;
		justify-content: space-between;
		border-top: 1px solid rgba(255, 255, 255, 0.04);
		border-bottom: 1px solid rgba(255, 255, 255, 0.04);
		background: rgba(0, 0, 0, 0.15);
	}

	.feed-count-label {
		font-size: 0.68rem;
		color: #94a3b8;
	}

	.recluster-btn {
		background: rgba(59, 130, 246, 0.1);
		border: 1px solid rgba(59, 130, 246, 0.3);
		color: #93c5fd;
		font-size: 0.65rem;
		padding: 3px 8px;
		border-radius: 4px;
		cursor: pointer;
	}

	.recluster-btn:hover {
		background: rgba(59, 130, 246, 0.25);
		color: #ffffff;
	}

	.mini-spinner {
		display: inline-block;
		width: 10px;
		height: 10px;
		border: 2px solid rgba(255, 255, 255, 0.3);
		border-top-color: #ffffff;
		border-radius: 50%;
		animation: spin 0.8s linear infinite;
	}

	/* Branch Feed List */
	.branch-feed-list {
		flex: 1;
		overflow-y: auto;
		padding: 10px 16px 20px;
		display: flex;
		flex-direction: column;
		gap: 7px;
	}

	.branch-feed-list::-webkit-scrollbar {
		width: 4px;
	}

	.branch-feed-list::-webkit-scrollbar-thumb {
		background: rgba(255, 255, 255, 0.1);
		border-radius: 4px;
	}

	.branch-item-card {
		background: rgba(30, 41, 59, 0.4);
		border: 1px solid rgba(255, 255, 255, 0.05);
		border-radius: 8px;
		padding: 10px 11px;
		cursor: pointer;
		transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
		outline: none;
	}

	.branch-item-card:hover {
		background: rgba(30, 41, 59, 0.8);
		border-color: rgba(96, 165, 250, 0.3);
		transform: translateY(-1px);
	}

	.branch-item-card.selected {
		background: rgba(30, 58, 138, 0.3);
		border-color: #3b82f6;
		box-shadow: 0 0 12px rgba(59, 130, 246, 0.2);
	}

	.card-top-row {
		display: flex;
		align-items: flex-start;
		justify-content: space-between;
		gap: 8px;
		margin-bottom: 5px;
	}

	.branch-name {
		font-size: 0.78rem;
		font-weight: 600;
		color: #f1f5f9;
		line-height: 1.3;
	}

	.density-badge {
		font-size: 0.6rem;
		font-weight: 700;
		padding: 2px 6px;
		border-radius: 4px;
		white-space: nowrap;
	}

	.branch-address {
		font-size: 0.68rem;
		color: #94a3b8;
		line-height: 1.4;
		margin-bottom: 6px;
	}

	.card-footer-meta {
		display: flex;
		align-items: center;
		justify-content: space-between;
		font-size: 0.62rem;
	}

	.meta-left {
		display: flex;
		align-items: center;
		gap: 6px;
	}

	.kat-tag {
		font-size: 0.58rem;
		font-weight: 600;
		padding: 1px 5px;
		border-radius: 3px;
	}

	.region-tag {
		color: #64748b;
	}

	.coord-tag {
		font-family: 'JetBrains Mono', monospace;
		color: #38bdf8;
		background: rgba(56, 189, 248, 0.08);
		padding: 1px 4px;
		border-radius: 3px;
	}

	.load-more-wrap {
		padding: 10px 0;
		display: flex;
		justify-content: center;
	}

	.btn-load-more {
		background: rgba(59, 130, 246, 0.15);
		border: 1px solid rgba(59, 130, 246, 0.3);
		color: #93c5fd;
		padding: 8px 14px;
		border-radius: 6px;
		font-size: 0.7rem;
		cursor: pointer;
		transition: all 0.2s;
	}

	.btn-load-more:hover {
		background: rgba(59, 130, 246, 0.3);
		color: #ffffff;
	}

	/* Loading & Empty States */
	.feed-loading-state,
	.feed-empty-state {
		display: flex;
		flex-direction: column;
		align-items: center;
		justify-content: center;
		padding: 40px 20px;
		text-align: center;
		color: #94a3b8;
		font-size: 0.8rem;
		gap: 12px;
	}

	.pulse-loader {
		width: 30px;
		height: 30px;
		border: 3px solid rgba(59, 130, 246, 0.2);
		border-top-color: #3b82f6;
		border-radius: 50%;
		animation: spin 1s linear infinite;
	}

	.btn-reset-filters {
		background: rgba(255, 255, 255, 0.1);
		border: none;
		color: #ffffff;
		padding: 6px 12px;
		border-radius: 6px;
		font-size: 0.72rem;
		cursor: pointer;
	}

	/* Map Viewport & 3D Tilt Perspective */
	.map-viewport {
		flex: 1;
		height: 100vh;
		position: relative;
		background: #0b0f19;
		overflow: hidden;
		perspective: 1200px;
	}

	#map-container {
		position: absolute;
		top: 0;
		left: 0;
		right: 0;
		bottom: 0;
		width: 100%;
		height: 100%;
		z-index: 1;
		background: #0f172a;
		transition: transform 0.6s cubic-bezier(0.16, 1, 0.3, 1);
		transform-origin: center bottom;
	}

	/* Statskog 3D Perspective Tilt */
	.map-viewport.tilt-3d-active #map-container {
		transform: rotateX(28deg) scale(1.08) translateY(-20px);
	}

	/* HUD Panel */
	.map-hud-panel {
		position: absolute;
		top: 20px;
		right: 20px;
		z-index: 999;
		background: rgba(15, 23, 42, 0.88);
		backdrop-filter: blur(16px);
		-webkit-backdrop-filter: blur(16px);
		border: 1px solid rgba(255, 255, 255, 0.1);
		border-radius: 12px;
		padding: 13px 15px;
		width: 330px;
		box-shadow: 0 10px 25px rgba(0, 0, 0, 0.5);
	}

	.hud-header {
		display: flex;
		align-items: center;
		justify-content: space-between;
		margin-bottom: 10px;
	}

	.hud-title {
		font-size: 0.63rem;
		font-weight: 700;
		color: #94a3b8;
		letter-spacing: 0.08em;
	}

	.hud-header-actions {
		display: flex;
		align-items: center;
		gap: 4px;
	}

	.btn-hud-map-switch {
		background: rgba(255, 255, 255, 0.06);
		border: 1px solid rgba(255, 255, 255, 0.08);
		color: #94a3b8;
		font-size: 0.65rem;
		padding: 3px 6px;
		border-radius: 4px;
		cursor: pointer;
		transition: all 0.2s;
	}

	.btn-hud-map-switch.active {
		background: rgba(59, 130, 246, 0.25);
		border-color: #3b82f6;
		color: #60a5fa;
		font-weight: 600;
	}

	.btn-hud-reset {
		display: flex;
		align-items: center;
		gap: 4px;
		background: rgba(255, 255, 255, 0.08);
		border: 1px solid rgba(255, 255, 255, 0.1);
		color: #cbd5e1;
		font-size: 0.65rem;
		padding: 3px 7px;
		border-radius: 4px;
		cursor: pointer;
	}

	.hud-layers {
		display: flex;
		gap: 5px;
		margin-bottom: 10px;
	}

	.layer-toggle {
		flex: 1;
		display: flex;
		align-items: center;
		justify-content: center;
		gap: 4px;
		background: rgba(30, 41, 59, 0.6);
		border: 1px solid rgba(255, 255, 255, 0.06);
		color: #94a3b8;
		font-size: 0.63rem;
		padding: 5px 4px;
		border-radius: 6px;
		cursor: pointer;
	}

	.layer-toggle.active {
		background: rgba(30, 41, 59, 0.95);
		border-color: var(--zone-color);
		color: #f8fafc;
	}

	.layer-dot {
		width: 6px;
		height: 6px;
		border-radius: 50%;
	}

	.hud-bar-wrap {
		display: flex;
		flex-direction: column;
		gap: 6px;
	}

	.hud-bar-label {
		display: flex;
		justify-content: space-between;
		font-size: 0.62rem;
		color: #94a3b8;
	}

	.multi-progress-bar {
		display: flex;
		height: 6px;
		border-radius: 3px;
		overflow: hidden;
		background: rgba(255, 255, 255, 0.05);
	}

	.bar-segment {
		height: 100%;
		transition: width 0.4s ease;
	}

	/* Toast Notification */
	.toast-banner {
		position: absolute;
		bottom: 24px;
		left: 50%;
		transform: translateX(-50%);
		z-index: 1001;
		background: rgba(15, 23, 42, 0.92);
		backdrop-filter: blur(12px);
		border: 1px solid rgba(255, 255, 255, 0.12);
		border-radius: 10px;
		padding: 10px 18px;
		display: flex;
		align-items: center;
		gap: 10px;
		box-shadow: 0 10px 25px rgba(0, 0, 0, 0.5);
		animation: slide-up 0.3s cubic-bezier(0.16, 1, 0.3, 1);
	}

	.toast-indicator {
		width: 8px;
		height: 8px;
		border-radius: 50%;
		background: #3b82f6;
	}

	.toast-text {
		font-size: 0.78rem;
		color: #f8fafc;
	}

	.toast-close {
		background: none;
		border: none;
		color: #94a3b8;
		font-size: 1.1rem;
		cursor: pointer;
	}

	/* Leaflet Globals */
	:global(.leaflet-container) {
		background: #0f172a !important;
		font-family: inherit !important;
		width: 100% !important;
		height: 100% !important;
	}

	:global(.custom-spatial-marker) {
		background: transparent !important;
		border: none !important;
	}

	:global(.marker-container) {
		position: relative;
		width: 28px;
		height: 28px;
		display: flex;
		align-items: center;
		justify-content: center;
	}

	:global(.marker-pulse) {
		position: absolute;
		width: 24px;
		height: 24px;
		border-radius: 50%;
		background: var(--zone-color);
		opacity: 0.35;
		animation: radar-pulse 2.2s infinite ease-out;
	}

	:global(.marker-core) {
		width: 18px;
		height: 18px;
		border-radius: 50%;
		background: #0f172a;
		border: 2px solid var(--zone-color);
		box-shadow: 0 0 10px var(--zone-glow);
		display: flex;
		align-items: center;
		justify-content: center;
		color: #ffffff;
		z-index: 2;
		transition: transform 0.2s;
	}

	:global(.marker-metric) {
		font-size: 0.58rem;
		font-weight: 700;
		font-family: 'JetBrains Mono', monospace;
		line-height: 1;
	}

	:global(.marker-container:hover .marker-core) {
		transform: scale(1.35);
	}

	:global(.leaflet-popup-content-wrapper) {
		background: rgba(15, 23, 42, 0.95) !important;
		backdrop-filter: blur(16px);
		border: 1px solid rgba(255, 255, 255, 0.15) !important;
		border-radius: 12px !important;
		box-shadow: 0 15px 30px rgba(0, 0, 0, 0.6) !important;
		color: #f8fafc !important;
		padding: 4px !important;
	}

	:global(.leaflet-popup-tip) {
		background: rgba(15, 23, 42, 0.95) !important;
	}

	:global(.spatial-popup-card) {
		display: flex;
		flex-direction: column;
		gap: 6px;
		padding: 4px;
	}

	:global(.popup-badges-row) {
		display: flex;
		align-items: center;
		gap: 5px;
	}

	:global(.popup-badge),
	:global(.popup-kat-badge) {
		font-size: 0.62rem;
		font-weight: 700;
		padding: 2px 6px;
		border-radius: 4px;
	}

	:global(.popup-title) {
		font-size: 0.85rem;
		font-weight: 700;
		color: #ffffff;
		margin: 0;
		line-height: 1.3;
	}

	:global(.popup-address) {
		font-size: 0.7rem;
		color: #94a3b8;
		margin: 0;
		line-height: 1.4;
	}

	:global(.popup-meta) {
		display: flex;
		align-items: center;
		justify-content: space-between;
		font-size: 0.63rem;
		margin-top: 4px;
		padding-top: 6px;
		border-top: 1px solid rgba(255, 255, 255, 0.08);
	}

	:global(.popup-region) {
		color: #64748b;
	}

	:global(.popup-coords) {
		font-family: 'JetBrains Mono', monospace;
		color: #38bdf8;
	}

	:global(.popup-gmaps-btn) {
		display: inline-flex;
		align-items: center;
		justify-content: center;
		gap: 6px;
		margin-top: 8px;
		padding: 7px 12px;
		background: linear-gradient(135deg, #2563eb, #1d4ed8);
		color: #ffffff !important;
		font-size: 0.72rem;
		font-weight: 600;
		text-decoration: none;
		border-radius: 6px;
		box-shadow: 0 4px 12px rgba(37, 99, 235, 0.35);
		transition: all 0.2s ease;
		border: 1px solid rgba(255, 255, 255, 0.15);
	}

	:global(.popup-gmaps-btn:hover) {
		background: linear-gradient(135deg, #3b82f6, #2563eb);
		transform: translateY(-1px);
		box-shadow: 0 6px 16px rgba(37, 99, 235, 0.5);
	}

	.meta-right {
		display: flex;
		align-items: center;
	}

	.card-gmaps-btn {
		display: inline-flex;
		align-items: center;
		gap: 4px;
		font-size: 0.65rem;
		font-weight: 600;
		color: #60a5fa;
		background: rgba(37, 99, 235, 0.12);
		border: 1px solid rgba(59, 130, 246, 0.3);
		padding: 3px 8px;
		border-radius: 4px;
		text-decoration: none;
		transition: all 0.15s ease;
	}

	.card-gmaps-btn:hover {
		background: rgba(37, 99, 235, 0.28);
		border-color: #60a5fa;
		color: #ffffff;
		transform: translateY(-1px);
	}

	/* Floating Detail Drawer (Bottom Left) */
	.floating-detail-drawer {
		position: absolute;
		bottom: 24px;
		left: 24px;
		width: 360px;
		max-width: calc(100% - 48px);
		background: rgba(15, 23, 42, 0.94);
		backdrop-filter: blur(20px);
		border: 1px solid rgba(255, 255, 255, 0.15);
		border-radius: 14px;
		padding: 16px;
		z-index: 1000;
		box-shadow: 0 20px 40px rgba(0, 0, 0, 0.65);
		display: flex;
		flex-direction: column;
		gap: 10px;
		animation: slide-up 0.25s cubic-bezier(0.16, 1, 0.3, 1);
	}

	.drawer-header {
		display: flex;
		align-items: center;
		justify-content: space-between;
		gap: 8px;
	}

	.drawer-badges {
		display: flex;
		align-items: center;
		gap: 6px;
		flex-wrap: wrap;
	}

	.kat-badge {
		font-size: 0.62rem;
		font-weight: 700;
		padding: 2px 7px;
		border-radius: 4px;
	}

	.btn-close-drawer {
		background: rgba(255, 255, 255, 0.08);
		border: 1px solid rgba(255, 255, 255, 0.1);
		color: #94a3b8;
		border-radius: 50%;
		width: 24px;
		height: 24px;
		display: flex;
		align-items: center;
		justify-content: center;
		cursor: pointer;
		font-size: 0.8rem;
		transition: all 0.15s;
	}

	.btn-close-drawer:hover {
		background: rgba(239, 68, 68, 0.2);
		border-color: #ef4444;
		color: #f87171;
	}

	.drawer-title {
		font-size: 0.98rem;
		font-weight: 700;
		color: #ffffff;
		margin: 0;
		line-height: 1.3;
	}

	.drawer-address {
		font-size: 0.76rem;
		color: #94a3b8;
		margin: 0;
		line-height: 1.45;
	}

	.drawer-actions {
		display: flex;
		align-items: center;
		justify-content: space-between;
		margin-top: 4px;
		padding-top: 10px;
		border-top: 1px solid rgba(255, 255, 255, 0.08);
	}

	.drawer-region {
		font-size: 0.72rem;
		color: #64748b;
	}

	.btn-drawer-gmaps {
		display: inline-flex;
		align-items: center;
		gap: 6px;
		padding: 7px 14px;
		background: linear-gradient(135deg, #2563eb, #1d4ed8);
		color: #ffffff;
		font-size: 0.75rem;
		font-weight: 600;
		border-radius: 8px;
		text-decoration: none;
		box-shadow: 0 4px 12px rgba(37, 99, 235, 0.35);
		transition: all 0.2s ease;
		border: 1px solid rgba(255, 255, 255, 0.15);
	}

	.btn-drawer-gmaps:hover {
		background: linear-gradient(135deg, #3b82f6, #2563eb);
		transform: translateY(-1px);
		box-shadow: 0 6px 18px rgba(37, 99, 235, 0.5);
	}

	@keyframes spin {
		to { transform: rotate(360deg); }
	}

	@keyframes pulse-ring {
		0%, 100% { opacity: 1; transform: scale(1); }
		50% { opacity: 0.4; transform: scale(1.3); }
	}

	@keyframes radar-pulse {
		0% { transform: scale(0.6); opacity: 0.8; }
		100% { transform: scale(1.8); opacity: 0; }
	}

	@keyframes slide-up {
		from { opacity: 0; transform: translate(-50%, 20px); }
		to { opacity: 1; transform: translate(-50%, 0); }
	}
</style>
