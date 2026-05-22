import { fireEvent, render, screen, waitFor, within } from '@testing-library/svelte';
import App from './App.svelte';

describe('App', () => {
  beforeEach(() => {
    vi.stubGlobal('fetch', vi.fn(() => Promise.reject(new Error('Capabilities unavailable'))));
  });

  afterEach(() => {
    window.history.replaceState({}, '', '/');
    vi.restoreAllMocks();
    vi.unstubAllGlobals();
  });

  function buildTelemetryGpxFile() {
    return new File(
      [
        `<?xml version="1.0" encoding="UTF-8"?>
        <gpx version="1.1" creator="test" xmlns="http://www.topografix.com/GPX/1/1">
          <trk><trkseg>
            <trkpt lat="49.0" lon="-123.0"><ele>10</ele><time>2024-01-01T00:00:00Z</time></trkpt>
            <trkpt lat="49.1" lon="-123.1"><ele>20</ele><time>2024-01-01T00:00:10Z</time></trkpt>
          </trkseg></trk>
        </gpx>`
      ],
      'track.gpx',
      { type: 'application/gpx+xml' }
    );
  }

  it('renders the trim page by default with header navigation', () => {
    render(App);

    const mainMenu = screen.getByRole('navigation', { name: /Main menu/i });

    expect(screen.getByRole('heading', { level: 1 })).toHaveTextContent('What do you want to do?');
    expect(screen.getByRole('heading', { level: 2, name: /Choose what you want to do/i })).toBeInTheDocument();
    expect(screen.getByRole('link', { name: /Trim GPX Cut a track/i })).toHaveAttribute('aria-current', 'step');
    expect(within(mainMenu).getByRole('link', { name: /^Trim GPX$/i })).toHaveAttribute(
      'aria-current',
      'page'
    );
    expect(within(mainMenu).getByRole('link', { name: /^Route animation$/i })).toBeInTheDocument();
    expect(within(mainMenu).getByRole('link', { name: /^Telemetry video$/i })).toBeInTheDocument();
    expect(screen.getByRole('heading', { level: 2, name: /^Trim GPX$/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Trim by time/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Split by videos/i })).toBeInTheDocument();
    expect(screen.getByLabelText(/Start time/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/End time/i)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Trim track/i })).toBeInTheDocument();

    expect(screen.getByLabelText(/^Video files$/i)).not.toBeVisible();
    expect(screen.queryByRole('button', { name: /Create ZIP/i })).not.toBeInTheDocument();
    expect(screen.getAllByLabelText(/^GPX file$/i)).toHaveLength(2);
    expect(screen.getByLabelText(/Optional video file/i)).toBeInTheDocument();
  });

  it('shows split-by-videos controls only after selecting that trim mode', async () => {
    render(App);

    await fireEvent.click(screen.getByRole('button', { name: /Split by videos/i }));

    expect(screen.getByLabelText(/^Video files$/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/^Video files$/i)).toBeVisible();
    expect(screen.getByRole('button', { name: /Create ZIP/i })).toBeInTheDocument();
    expect(screen.getByLabelText(/Start time/i)).not.toBeVisible();
    expect(screen.queryByRole('button', { name: /Trim track/i })).not.toBeInTheDocument();
    expect(screen.getAllByLabelText(/^GPX file$/i)).toHaveLength(2);
  });

  it('renders the route animation page from the hash route', async () => {
    window.location.hash = '#/animation';
    render(App);

    await waitFor(() => {
      expect(screen.getByRole('heading', { level: 2, name: /Create route animation/i })).toBeInTheDocument();
    });
    expect(
      within(screen.getByRole('navigation', { name: /Main menu/i })).getByRole('link', {
        name: /^Route animation$/i
      })
    ).toHaveAttribute('aria-current', 'page');
    expect(screen.getByLabelText(/Duration \(seconds\)/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/Frames per second/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/Resolution width/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/Resolution height/i)).toBeInTheDocument();
    const tileStyleSelect = screen.getByLabelText(/Tile style/i);
    expect(tileStyleSelect).toBeInTheDocument();
    expect(tileStyleSelect).toHaveValue('osm');
    expect(screen.queryByRole('option', { name: /Backend default/i })).not.toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Render animation/i })).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /Trim by time/i })).not.toBeInTheDocument();
  });

  it('shows the selected marker color in the route animation style controls', async () => {
    window.location.hash = '#/animation';
    render(App);

    await waitFor(() => {
      expect(screen.getByLabelText(/Marker color/i)).toBeInTheDocument();
    });
    const markerColorInput = screen.getByLabelText(/Marker color/i);

    await fireEvent.input(markerColorInput, { target: { value: '#ff0000' } });

    expect(screen.getByText('#ff0000')).toBeInTheDocument();
    expect(markerColorInput).toHaveValue('#ff0000');
  });

  it('renders the telemetry video page from the hash route', async () => {
    window.location.hash = '#/telemetry';
    render(App);

    await waitFor(() => {
      expect(screen.getByRole('heading', { level: 2, name: /Generate telemetry video/i })).toBeInTheDocument();
    });
    expect(
      within(screen.getByRole('navigation', { name: /Main menu/i })).getByRole('link', {
        name: /^Telemetry video$/i
      })
    ).toHaveAttribute('aria-current', 'page');
    expect(screen.getByLabelText(/Telemetry video type/i)).toBeInTheDocument();
    await fireEvent.click(screen.getByText(/Advanced settings/i));
    expect(screen.getByText(/Background mode/i)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /^Transparent$/i })).toHaveAttribute('aria-pressed', 'true');
    expect(screen.getByRole('button', { name: /^Custom color$/i })).toHaveAttribute('aria-pressed', 'false');
    expect(screen.getByRole('button', { name: /Render telemetry video/i })).toBeInTheDocument();
  });

  it('fills the telemetry duration from the uploaded gpx timestamps on the frontend', async () => {
    window.location.hash = '#/telemetry';
    render(App);

    await waitFor(() => {
      expect(screen.getByRole('heading', { level: 2, name: /Generate telemetry video/i })).toBeInTheDocument();
    });

    const fileInput = screen.getByLabelText(/^GPX file$/i);
    const durationInput = screen.getByLabelText(/Duration \(seconds\)/i);
    const gpxFile = buildTelemetryGpxFile();

    await fireEvent.change(fileInput, { target: { files: [gpxFile] } });

    await waitFor(() => {
      expect(durationInput).toHaveValue(10);
    });
  });
});
