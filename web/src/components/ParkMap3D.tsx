import React, { useEffect, useRef, useState } from 'react';
import maplibregl from 'maplibre-gl';
import {
  OLYMPIC_PARK_VENUES,
  PARKING_ZONES,
  SUBWAY_STATIONS,
  makeCirclePolygon,
  makeRectPolygon,
} from '../data/parkGeometry';
import type { Lang, ZoneEmpirical } from '../types';

export interface ZoneDynamicState {
  zone: string;
  loadPct: number; // 0..115
  status: 'smooth' | 'congested' | 'full';
  estVehicles: number;
  empiricalFullPct: number;
  gateKo: string;
  gateEn: string;
  walkToKspoMin: number;
  isOverflowTarget: boolean;
}

interface ParkMap3DProps {
  lang: Lang;
  predictedTotalParking: number;
  zonesEmpirical: ZoneEmpirical[];
  highlightOverflow?: boolean;
  onSelectZone?: (z: ZoneDynamicState) => void;
}

export function computeZoneStates(
  predictedTotalParking: number,
  zonesEmpirical: ZoneEmpirical[]
): ZoneDynamicState[] {
  const empMap = new Map(zonesEmpirical.map((z) => [z.zone, z]));
  const parkCapacityRef = 3330; // Sum of 11 zone capacities
  const parkLoadRatio = predictedTotalParking / parkCapacityRef;

  return PARKING_ZONES.map((meta) => {
    const emp = empMap.get(meta.zone);
    const empFull = emp ? emp.full_rate_pct : 35;
    const empBusy = emp ? emp.busy_or_full_pct : 70;
    // Spatial asymmetry factor derived directly from 15164156_parking_congestion.csv
    const spatialFactor = empBusy / 71.8;
    const rawPct = Math.min(115, Math.max(8, Math.round(parkLoadRatio * 100 * spatialFactor)));
    const status: 'smooth' | 'congested' | 'full' =
      rawPct >= 88 ? 'full' : rawPct >= 65 ? 'congested' : 'smooth';
    const estVehicles = Math.min(
      meta.capacityEst,
      Math.round((meta.capacityEst * Math.min(100, rawPct)) / 100)
    );
    return {
      zone: meta.zone,
      loadPct: rawPct,
      status,
      estVehicles,
      empiricalFullPct: empFull,
      gateKo: meta.gateKo,
      gateEn: meta.gateEn,
      walkToKspoMin: meta.walkToKspoMin,
      isOverflowTarget: meta.isOverflowTarget,
    };
  });
}

function buildZonesGeoJSON(states: ZoneDynamicState[]): GeoJSON.FeatureCollection {
  const mapState = new Map(states.map((s) => [s.zone, s]));
  return {
    type: 'FeatureCollection',
    features: PARKING_ZONES.map((z) => {
      const st = mapState.get(z.zone);
      const load = st?.loadPct ?? 40;
      const color =
        st?.status === 'full'
          ? '#f43f5e'
          : st?.status === 'congested'
            ? '#f59e0b'
            : '#10b981';
      return {
        type: 'Feature',
        properties: {
          zone: z.zone,
          label: `${z.zone} (${load}%)`,
          loadPct: load,
          height: Math.max(12, Math.round(load * 1.15)),
          color,
          status: st?.status ?? 'smooth',
          isOverflowTarget: z.isOverflowTarget,
        },
        geometry: {
          type: 'Polygon',
          coordinates: makeRectPolygon(z.center, z.sizeLng, z.sizeLat),
        },
      };
    }),
  };
}

function buildVenuesGeoJSON(lang: Lang): GeoJSON.FeatureCollection {
  return {
    type: 'FeatureCollection',
    features: OLYMPIC_PARK_VENUES.map((v) => ({
      type: 'Feature',
      properties: {
        id: v.id,
        name: lang === 'ko' ? v.nameKo : v.nameEn,
        height: v.heightM,
        color: v.color,
        capacity: v.capacity,
      },
      geometry: {
        type: 'Polygon',
        coordinates: makeCirclePolygon(v.center, v.radiusLng, v.radiusLat, 24),
      },
    })),
  };
}

function buildSubwayGeoJSON(lang: Lang): GeoJSON.FeatureCollection {
  return {
    type: 'FeatureCollection',
    features: SUBWAY_STATIONS.map((s) => ({
      type: 'Feature',
      properties: {
        id: s.id,
        name: `${lang === 'ko' ? s.nameKo : s.nameEn} (${s.lines})`,
      },
      geometry: {
        type: 'Point',
        coordinates: s.center,
      },
    })),
  };
}

export const ParkMap3D: React.FC<ParkMap3DProps> = ({
  lang,
  predictedTotalParking,
  zonesEmpirical,
  onSelectZone,
}) => {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const mapRef = useRef<maplibregl.Map | null>(null);
  const readyRef = useRef(false);
  const [selected, setSelected] = useState<ZoneDynamicState | null>(null);
  const [viewMode, setViewMode] = useState<'3d' | 'kspo' | 'overflow' | '2d'>('3d');

  const zoneStates = computeZoneStates(predictedTotalParking, zonesEmpirical);
  const zoneStatesRef = useRef(zoneStates);
  zoneStatesRef.current = zoneStates;

  useEffect(() => {
    if (!containerRef.current || mapRef.current) return;

    const map = new maplibregl.Map({
      container: containerRef.current,
      style: 'https://basemaps.cartocdn.com/gl/dark-matter-gl-style/style.json',
      center: [127.1232, 37.5186],
      zoom: 14.85,
      pitch: 54,
      bearing: -18,
      antialias: true,
      attributionControl: false,
    });
    mapRef.current = map;

    map.addControl(new maplibregl.AttributionControl({ compact: true }), 'bottom-right');
    map.addControl(new maplibregl.NavigationControl({ visualizePitch: true }), 'top-right');

    map.on('load', () => {
      readyRef.current = true;

      // 1. Venues 3D extrusion
      map.addSource('venues', {
        type: 'geojson',
        data: buildVenuesGeoJSON(lang),
      });
      map.addLayer({
        id: 'venues-3d',
        type: 'fill-extrusion',
        source: 'venues',
        paint: {
          'fill-extrusion-color': ['get', 'color'],
          'fill-extrusion-height': ['get', 'height'],
          'fill-extrusion-base': 0,
          'fill-extrusion-opacity': 0.58,
        },
      });
      map.addLayer({
        id: 'venues-label',
        type: 'symbol',
        source: 'venues',
        layout: {
          'text-field': ['get', 'name'],
          'text-size': 11,
          'text-offset': [0, 0],
        },
        paint: {
          'text-color': '#e2e8f0',
          'text-halo-color': '#020617',
          'text-halo-width': 1.5,
        },
      });

      // 2. 11 Parking Zones 3D dynamic towers
      map.addSource('parking-zones', {
        type: 'geojson',
        data: buildZonesGeoJSON(zoneStatesRef.current),
      });
      map.addLayer({
        id: 'parking-3d',
        type: 'fill-extrusion',
        source: 'parking-zones',
        paint: {
          'fill-extrusion-color': ['get', 'color'],
          'fill-extrusion-height': ['get', 'height'],
          'fill-extrusion-base': 0,
          'fill-extrusion-opacity': 0.88,
        },
      });
      map.addLayer({
        id: 'parking-label',
        type: 'symbol',
        source: 'parking-zones',
        layout: {
          'text-field': ['get', 'label'],
          'text-size': 11,
          'text-allow-overlap': true,
        },
        paint: {
          'text-color': '#ffffff',
          'text-halo-color': '#0f172a',
          'text-halo-width': 2,
        },
      });

      // 3. Subway stations
      map.addSource('subways', {
        type: 'geojson',
        data: buildSubwayGeoJSON(lang),
      });
      map.addLayer({
        id: 'subways-circle',
        type: 'circle',
        source: 'subways',
        paint: {
          'circle-radius': 7,
          'circle-color': '#38bdf8',
          'circle-stroke-width': 2,
          'circle-stroke-color': '#0f172a',
        },
      });
      map.addLayer({
        id: 'subways-label',
        type: 'symbol',
        source: 'subways',
        layout: {
          'text-field': ['get', 'name'],
          'text-size': 11,
          'text-offset': [0, 1.4],
        },
        paint: {
          'text-color': '#7dd3fc',
          'text-halo-color': '#020617',
          'text-halo-width': 1.5,
        },
      });

      map.on('click', 'parking-3d', (e) => {
        const zCode = e.features?.[0]?.properties?.zone;
        const found = zoneStatesRef.current.find((s) => s.zone === zCode);
        if (found) {
          setSelected(found);
          onSelectZone?.(found);
        }
      });
      map.on('mouseenter', 'parking-3d', () => {
        map.getCanvas().style.cursor = 'pointer';
      });
      map.on('mouseleave', 'parking-3d', () => {
        map.getCanvas().style.cursor = '';
      });
    });

    return () => {
      readyRef.current = false;
      map.remove();
      mapRef.current = null;
    };
  }, []);

  // Update 3D parking towers whenever slider/scenario changes
  useEffect(() => {
    const map = mapRef.current;
    if (!map || !readyRef.current) return;
    const src = map.getSource('parking-zones') as maplibregl.GeoJSONSource | undefined;
    src?.setData(buildZonesGeoJSON(zoneStates));
    const vSrc = map.getSource('venues') as maplibregl.GeoJSONSource | undefined;
    vSrc?.setData(buildVenuesGeoJSON(lang));
    const sSrc = map.getSource('subways') as maplibregl.GeoJSONSource | undefined;
    sSrc?.setData(buildSubwayGeoJSON(lang));
  }, [predictedTotalParking, lang, zonesEmpirical]);

  const flyPreset = (mode: '3d' | 'kspo' | 'overflow' | '2d') => {
    setViewMode(mode);
    const map = mapRef.current;
    if (!map) return;
    if (mode === '3d') {
      map.flyTo({ center: [127.1232, 37.5186], zoom: 14.85, pitch: 54, bearing: -18, duration: 750 });
    } else if (mode === 'kspo') {
      map.flyTo({ center: [127.1274, 37.5184], zoom: 15.8, pitch: 60, bearing: -35, duration: 750 });
    } else if (mode === 'overflow') {
      map.flyTo({ center: [127.1168, 37.5174], zoom: 15.7, pitch: 52, bearing: 15, duration: 750 });
    } else {
      map.flyTo({ center: [127.1232, 37.5186], zoom: 14.7, pitch: 0, bearing: 0, duration: 700 });
    }
  };

  return (
    <div className="relative h-[440px] w-full overflow-hidden rounded-2xl border border-slate-800 bg-slate-900 shadow-2xl">
      <div ref={containerRef} className="h-full w-full" />

      {/* Camera Presets */}
      <div className="absolute left-3 top-3 flex flex-wrap gap-1.5 rounded-xl border border-slate-700/80 bg-slate-950/85 p-1.5 backdrop-blur-md">
        {[
          { k: '3d' as const, ko: '3D 전체 뷰', en: '3D Full Park' },
          { k: 'kspo' as const, ko: 'KSPO DOME·병목존', en: 'KSPO Bottleneck' },
          { k: 'overflow' as const, ko: 'P1A·P1B 여유존', en: 'P1A/P1B Overflow' },
          { k: '2d' as const, ko: '2D 평면', en: '2D Top' },
        ].map((btn) => (
          <button
            key={btn.k}
            onClick={() => flyPreset(btn.k)}
            className={`rounded-lg px-2.5 py-1 text-xs font-medium transition ${
              viewMode === btn.k
                ? 'bg-blue-600 text-white shadow'
                : 'text-slate-300 hover:bg-slate-800'
            }`}
          >
            {lang === 'ko' ? btn.ko : btn.en}
          </button>
        ))}
      </div>

      {/* Legend */}
      <div className="absolute bottom-3 left-3 flex items-center gap-3 rounded-xl border border-slate-700/80 bg-slate-950/85 px-3 py-2 text-[11px] text-slate-200 backdrop-blur-md">
        <span className="flex items-center gap-1.5">
          <span className="h-2.5 w-2.5 rounded-full bg-emerald-500" />
          {lang === 'ko' ? '원활 (<65%)' : 'Smooth'}
        </span>
        <span className="flex items-center gap-1.5">
          <span className="h-2.5 w-2.5 rounded-full bg-amber-500" />
          {lang === 'ko' ? '혼잡 (65~87%)' : 'Busy'}
        </span>
        <span className="flex items-center gap-1.5">
          <span className="h-2.5 w-2.5 rounded-full bg-rose-500" />
          {lang === 'ko' ? '만차 위험 (88%+)' : 'Full Risk'}
        </span>
        <span className="hidden border-l border-slate-700 pl-3 text-slate-400 sm:inline">
          {lang === 'ko' ? '우클릭 드래그: 3D 회전 · 기둥 클릭: 구역 상세' : 'Right-drag: 3D tilt · Click tower for details'}
        </span>
      </div>

      {/* Selected Zone Popover */}
      {selected && (
        <div className="absolute bottom-3 right-3 w-64 rounded-xl border border-blue-500/40 bg-slate-950/92 p-3 text-xs text-slate-100 shadow-xl backdrop-blur-md">
          <div className="flex items-center justify-between">
            <span className="text-sm font-bold text-white">
              {selected.zone} · {lang === 'ko' ? selected.gateKo : selected.gateEn}
            </span>
            <button onClick={() => setSelected(null)} className="text-slate-400 hover:text-white">
              ✕
            </button>
          </div>
          <div className="mt-2 grid grid-cols-2 gap-2">
            <div className="rounded-lg bg-slate-900 p-2">
              <div className="text-[10px] text-slate-400">{lang === 'ko' ? '예측 혼잡도' : 'Predicted Load'}</div>
              <div className="text-base font-bold text-blue-400">{selected.loadPct}%</div>
            </div>
            <div className="rounded-lg bg-slate-900 p-2">
              <div className="text-[10px] text-slate-400">{lang === 'ko' ? '실측 만차율' : 'Historical Full'}</div>
              <div className="text-base font-bold text-rose-400">{selected.empiricalFullPct}%</div>
            </div>
          </div>
          <div className="mt-2 text-[11px] text-slate-300">
            {lang === 'ko'
              ? `KSPO DOME 도보 약 ${selected.walkToKspoMin}분 · 추정 주차 ${selected.estVehicles}대`
              : `~${selected.walkToKspoMin} min walk to KSPO DOME · Est. ${selected.estVehicles} cars`}
          </div>
          {selected.isOverflowTarget && (
            <div className="mt-1.5 rounded bg-emerald-500/20 px-2 py-1 text-[11px] font-medium text-emerald-300">
              {lang === 'ko' ? '✓ 공단 분산 권장 여유 구역 (P11 대비 -26.5%p)' : '✓ Recommended Dispersion Zone (-26.5%p vs P11)'}
            </div>
          )}
        </div>
      )}
    </div>
  );
};
