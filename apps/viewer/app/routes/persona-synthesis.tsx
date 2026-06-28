import { useMutation, useQuery } from "@tanstack/react-query";
import { CheckCircle2, Copy, Play, RefreshCw, XCircle } from "lucide-react";
import type { FormEvent } from "react";
import { useMemo, useState } from "react";
import { toast } from "sonner";

import {
  BreadcrumbItem,
  BreadcrumbList,
  PageBreadcrumb,
  PageHeader,
  PageHeaderActions,
  PageHeaderMeta,
  PageHeaderMetaPrimary,
  PageHeaderRow,
  PageShell,
  PageTitle,
} from "~/components/page-header";
import { TruncatedBreadcrumbPage } from "~/components/truncated-breadcrumb";
import { Badge } from "~/components/ui/badge";
import { Button } from "~/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "~/components/ui/card";
import { Input } from "~/components/ui/input";
import { Label } from "~/components/ui/label";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "~/components/ui/table";
import {
  fetchPersonaSynthesisInfo,
  runPersonaSynthesis,
  type PersonaSynthesisRequest,
} from "~/lib/api";

function formatNumber(value: number | null | undefined): string {
  return typeof value === "number" ? value.toLocaleString() : "-";
}

function compactPath(path: string): string {
  return path.replaceAll("\\", "/");
}

function StatBlock({
  label,
  value,
  detail,
}: {
  label: string;
  value: string;
  detail?: string;
}) {
  return (
    <div className="min-w-0 border border-border bg-card px-3 py-2">
      <div className="text-xs text-muted-foreground">{label}</div>
      <div className="mt-1 truncate text-lg font-medium tabular-nums">
        {value}
      </div>
      {detail && <div className="mt-1 truncate text-xs text-muted-foreground">{detail}</div>}
    </div>
  );
}

async function copyToClipboard(value: string, label: string) {
  await navigator.clipboard.writeText(value);
  toast(label);
}

export default function PersonaSynthesis() {
  const [count, setCount] = useState(10);
  const [seed, setSeed] = useState(42);
  const [outputName, setOutputName] = useState("synthetic-human-ui");
  const [maxAttempts, setMaxAttempts] = useState(1000);
  const [previewDimensions, setPreviewDimensions] = useState(32);

  const { data: info, isLoading: isInfoLoading } = useQuery({
    queryKey: ["persona-synthesis-info"],
    queryFn: fetchPersonaSynthesisInfo,
    staleTime: Infinity,
  });

  const mutation = useMutation({
    mutationFn: (request: PersonaSynthesisRequest) =>
      runPersonaSynthesis(request),
    onSuccess: (result) => {
      toast("Persona vectors generated", {
        description: `${formatNumber(result.count)} personas -> ${compactPath(result.output_dir)}`,
      });
    },
    onError: (error) => {
      toast.error("Synthesis failed", { description: error.message });
    },
  });

  const result = mutation.data;
  const constraintValidation = result?.constraint_validation.validation;
  const sampleRows = useMemo(
    () => Object.entries(result?.sample_dimensions ?? {}),
    [result?.sample_dimensions]
  );

  const submit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    mutation.mutate({
      count,
      seed,
      output_name: outputName.trim() || undefined,
      max_attempts_per_persona: maxAttempts,
      preview_dimensions: previewDimensions,
    });
  };

  return (
    <PageShell>
      <PageBreadcrumb>
        <BreadcrumbList>
          <BreadcrumbItem>
            <TruncatedBreadcrumbPage title="Persona Synthesis">
              Persona Synthesis
            </TruncatedBreadcrumbPage>
          </BreadcrumbItem>
        </BreadcrumbList>
      </PageBreadcrumb>

      <PageHeader>
        <PageHeaderRow>
          <PageTitle>Persona Synthesis</PageTitle>
          <PageHeaderActions>
            <Badge variant="outline">
              {isInfoLoading
                ? "Loading schema"
                : `${formatNumber(info?.dimension_count)} dimensions`}
            </Badge>
            <Badge variant="outline">
              {isInfoLoading
                ? "Loading rules"
                : `${formatNumber(info?.constraint_count)} constraints`}
            </Badge>
          </PageHeaderActions>
        </PageHeaderRow>
        <PageHeaderMeta>
          <PageHeaderMetaPrimary>
            <span>Schema {info?.schema_version ?? "-"}</span>
            <span className="text-border">|</span>
            <span>{info?.dimension_set ?? "all-catalog-dimensions"}</span>
          </PageHeaderMetaPrimary>
        </PageHeaderMeta>
      </PageHeader>

      <div className="grid min-w-0 grid-cols-1 gap-4 px-4 sm:px-0 lg:grid-cols-[360px_minmax(0,1fr)]">
        <Card>
          <CardHeader>
            <CardTitle>Run</CardTitle>
            <CardDescription>
              Full-catalog random sampling with pairwise rejection.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <form className="grid gap-4" onSubmit={submit}>
              <div className="grid gap-2">
                <Label htmlFor="count">Count</Label>
                <Input
                  id="count"
                  type="number"
                  min={1}
                  max={1000}
                  value={count}
                  onChange={(event) => setCount(Number(event.target.value))}
                />
              </div>
              <div className="grid gap-2">
                <Label htmlFor="seed">Seed</Label>
                <Input
                  id="seed"
                  type="number"
                  value={seed}
                  onChange={(event) => setSeed(Number(event.target.value))}
                />
              </div>
              <div className="grid gap-2">
                <Label htmlFor="output-name">Output name</Label>
                <Input
                  id="output-name"
                  value={outputName}
                  onChange={(event) => setOutputName(event.target.value)}
                  placeholder="synthetic-human-ui"
                />
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div className="grid gap-2">
                  <Label htmlFor="max-attempts">Attempts</Label>
                  <Input
                    id="max-attempts"
                    type="number"
                    min={1}
                    max={10000}
                    value={maxAttempts}
                    onChange={(event) =>
                      setMaxAttempts(Number(event.target.value))
                    }
                  />
                </div>
                <div className="grid gap-2">
                  <Label htmlFor="preview-dimensions">Preview</Label>
                  <Input
                    id="preview-dimensions"
                    type="number"
                    min={1}
                    max={200}
                    value={previewDimensions}
                    onChange={(event) =>
                      setPreviewDimensions(Number(event.target.value))
                    }
                  />
                </div>
              </div>
              <Button
                type="submit"
                disabled={mutation.isPending || isInfoLoading}
                className="mt-2 w-full"
              >
                {mutation.isPending ? (
                  <RefreshCw className="h-4 w-4 animate-spin" />
                ) : (
                  <Play className="h-4 w-4" />
                )}
                Generate
              </Button>
            </form>
          </CardContent>
        </Card>

        <div className="grid min-w-0 gap-4">
          <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
            <StatBlock
              label="Schema"
              value={info?.schema_version ?? "-"}
              detail={info?.catalog_path}
            />
            <StatBlock
              label="Dimensions"
              value={formatNumber(info?.dimension_count)}
              detail={`${formatNumber(info?.target_dimensions)} target`}
            />
            <StatBlock
              label="Constraints"
              value={formatNumber(
                info?.constraint_validation
                  .applicable_to_generated_dimensions_count
              )}
              detail={`${formatNumber(info?.constraint_count)} source`}
            />
            <StatBlock
              label="Last attempts"
              value={formatNumber(result?.sampling.attempts)}
              detail={
                constraintValidation
                  ? `${formatNumber(constraintValidation.rejected_attempts)} rejected`
                  : "No run yet"
              }
            />
          </div>

          <Card>
            <CardHeader>
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div className="min-w-0">
                  <CardTitle>Result</CardTitle>
                  <CardDescription>
                    {result
                      ? `${formatNumber(result.count)} personas generated`
                      : "No dataset generated in this session."}
                  </CardDescription>
                </div>
                {constraintValidation && (
                  <Badge
                    variant={
                      constraintValidation.status === "passed"
                        ? "secondary"
                        : "destructive"
                    }
                  >
                    {constraintValidation.status === "passed" ? (
                      <CheckCircle2 className="h-3 w-3" />
                    ) : (
                      <XCircle className="h-3 w-3" />
                    )}
                    {constraintValidation.status}
                  </Badge>
                )}
              </div>
            </CardHeader>
            <CardContent className="grid gap-4">
              {result ? (
                <>
                  <div className="grid gap-2 text-sm">
                    <div className="flex min-w-0 items-center gap-2">
                      <span className="w-24 shrink-0 text-muted-foreground">
                        Output
                      </span>
                      <code className="min-w-0 flex-1 truncate border border-border bg-muted px-2 py-1 text-xs">
                        {compactPath(result.output_dir)}
                      </code>
                      <Button
                        type="button"
                        variant="ghost"
                        size="icon-sm"
                        onClick={() =>
                          copyToClipboard(result.output_dir, "Output path copied")
                        }
                      >
                        <Copy className="h-4 w-4" />
                      </Button>
                    </div>
                    <div className="flex min-w-0 items-center gap-2">
                      <span className="w-24 shrink-0 text-muted-foreground">
                        Manifest
                      </span>
                      <code className="min-w-0 flex-1 truncate border border-border bg-muted px-2 py-1 text-xs">
                        {compactPath(result.manifest_path)}
                      </code>
                      <Button
                        type="button"
                        variant="ghost"
                        size="icon-sm"
                        onClick={() =>
                          copyToClipboard(
                            result.manifest_path,
                            "Manifest path copied"
                          )
                        }
                      >
                        <Copy className="h-4 w-4" />
                      </Button>
                    </div>
                  </div>

                  <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
                    <StatBlock
                      label="Personas"
                      value={formatNumber(result.count)}
                      detail={`seed ${result.seed}`}
                    />
                    <StatBlock
                      label="Fields each"
                      value={formatNumber(result.dimension_count)}
                      detail={result.dimension_set}
                    />
                    <StatBlock
                      label="Rejected"
                      value={formatNumber(
                        constraintValidation?.rejected_attempts
                      )}
                      detail="constraint hits"
                    />
                    <StatBlock
                      label="Schema rejects"
                      value={formatNumber(
                        result.schema_grounding.validation.rejected_attempts
                      )}
                      detail={result.schema_grounding.validation.status}
                    />
                  </div>

                  <div className="min-w-0">
                    <div className="mb-2 flex flex-wrap items-center justify-between gap-2">
                      <div className="text-sm font-medium">
                        {result.sample_persona_id}
                      </div>
                      <div className="text-xs text-muted-foreground">
                        {formatNumber(sampleRows.length)} shown of{" "}
                        {formatNumber(result.sample_dimension_total)}
                      </div>
                    </div>
                    <div className="max-h-[420px] overflow-auto border border-border">
                      <Table>
                        <TableHeader>
                          <TableRow>
                            <TableHead className="w-[40%]">Dimension</TableHead>
                            <TableHead>Value</TableHead>
                          </TableRow>
                        </TableHeader>
                        <TableBody>
                          {sampleRows.map(([dimension, value]) => (
                            <TableRow key={dimension}>
                              <TableCell className="font-mono text-xs">
                                {dimension}
                              </TableCell>
                              <TableCell className="whitespace-normal break-words text-sm">
                                {value}
                              </TableCell>
                            </TableRow>
                          ))}
                        </TableBody>
                      </Table>
                    </div>
                  </div>
                </>
              ) : (
                <div className="flex min-h-[260px] items-center justify-center border border-dashed border-border text-sm text-muted-foreground">
                  Awaiting run
                </div>
              )}
            </CardContent>
          </Card>
        </div>
      </div>
    </PageShell>
  );
}
