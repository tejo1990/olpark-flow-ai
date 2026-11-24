export type Lang = 'ko' | 'en';
export type SeasonKey = 'spring' | 'summer' | 'autumn' | 'winter';
export type DayTypeKey = 'weekday' | 'weekend' | 'holiday';
export type ConcertTierKey = 'none' | 'small_3k' | 'medium_8k' | 'large_15k' | 'mega_25k';
export type WeatherKey = 'clear' | 'rain';

export interface MetricRow {
  mae: number;
  rmse: number;
  r2: number;
  peak_mape_pct: number;
}

export interface FeatureImportance {
  feature: string;
  importance_r2: number;
  std: number;
}

export interface BacktestPoint {
  hour: number;
  actual_parking: number;
  pred_parking: number;
  actual_visitors: number;
  pred_visitors: number;
  temp_c: number;
  precip_mm: number;
}

export interface BacktestCase {
  id: string;
  label: string;
  date: string;
  concert_name: string;
  max_audience: number;
  total_precip_mm: number;
  day_mae: number;
  series: BacktestPoint[];
}

export interface ZoneEmpirical {
  zone: string;
  total: number;
  full: number;
  congested: number;
  smooth: number;
  full_rate_pct: number;
  busy_or_full_pct: number;
}

export interface DQFinding {
  id: string;
  severity: 'HIGH' | 'MEDIUM' | 'LOW';
  title: string;
  detail: string;
}

export interface WebModelBundle {
  generated_at: string;
  data_quality_audit: {
    raw_rows_loaded: number;
    anomalous_months_excluded: number[];
    anomalous_rows_excluded: number;
    clean_rows_used: number;
    ext_2025_concert_days_matched?: number;
    findings: DQFinding[];
  };
  dataset_stats: {
    source: string;
    rows: number;
    unique_days: number;
    date_range: [string, string];
    concert_days: number;
    max_parking_hourly: number;
    max_visitors_hourly: number;
    max_concert_audience: number;
  };
  benchmarks: {
    parking_count: {
      train_rows: number;
      test_rows: number;
      oot_oct_dec: Record<string, MetricRow>;
      cv_5fold_day_grouped: Record<string, MetricRow>;
      feature_importance: FeatureImportance[];
    };
    visitor_count: {
      train_rows: number;
      test_rows: number;
      oot_oct_dec: Record<string, MetricRow>;
      cv_5fold_day_grouped: Record<string, MetricRow>;
      feature_importance: FeatureImportance[];
    };
  };
  backtest: {
    sample_days: BacktestCase[];
    top_2025_concerts: Array<{
      date_str: string;
      concert_name: string;
      max_aud: number;
      max_park: number;
      sum_rain: number;
    }>;
    monthly_backtest: Array<{
      month: number;
      rows: number;
      avg_actual: number;
      avg_pred: number;
      mae: number;
      r2: number;
    }>;
  };
  prediction_grid: {
    schema_key: string;
    model_used?: string;
    seasons: SeasonKey[];
    day_types: DayTypeKey[];
    concert_tiers: Record<ConcertTierKey, number>;
    weathers: WeatherKey[];
    curves: Record<string, { parking: number[]; visitors: number[] }>;
  };
  zones_11_empirical: ZoneEmpirical[];
  esg_baseline: {
    avg_exits_19_22_on_peak_day: number;
    assumed_queued_vehicles_40pct: number;
    assumed_avg_queue_min: number;
    co2_kg_per_min_factor: number;
    est_idling_co2_kg_per_peak_evening: number;
  };
}

export interface WebEventsBundle {
  generated_at: string;
  concerts_2026_en: Array<{
    id: string;
    title: string;
    date: string;
    views: number;
    poster: string;
    url: string;
  }>;
  lawn_facilities: Array<{
    name: string;
    hours: string;
    url: string;
  }>;
  recent_lost_items: Array<{
    title: string;
    place: string;
    date: string;
  }>;
}
