/**
 * Lightweight logging abstraction.
 *
 * Wraps console.* with severity levels and timestamps so that
 * log verbosity can be controlled centrally.
 */

type LogLevel = 'debug' | 'info' | 'warn' | 'error';

const LEVEL_PRIORITY: Record<LogLevel, number> = {
    debug: 0,
    info: 1,
    warn: 2,
    error: 3,
};

const currentLevel: LogLevel =
    (process.env.REACT_APP_LOG_LEVEL as LogLevel) || 'info';

function shouldLog(level: LogLevel): boolean {
    return LEVEL_PRIORITY[level] >= LEVEL_PRIORITY[currentLevel];
}

function formatPrefix(level: LogLevel, tag: string): string {
    return `${new Date().toISOString()} [${level.toUpperCase()}] ${tag}:`;
}

function createLogger(tag: string) {
    return {
        debug(...args: unknown[]) {
            if (shouldLog('debug')) console.debug(formatPrefix('debug', tag), ...args);
        },
        info(...args: unknown[]) {
            if (shouldLog('info')) console.info(formatPrefix('info', tag), ...args);
        },
        warn(...args: unknown[]) {
            if (shouldLog('warn')) console.warn(formatPrefix('warn', tag), ...args);
        },
        error(...args: unknown[]) {
            if (shouldLog('error')) console.error(formatPrefix('error', tag), ...args);
        },
    };
}

export default createLogger;
